import json
import base64
import logging
from typing import Literal, Optional
from pydantic import BaseModel, Field
import httpx
from google import genai
from google.genai import types

from app.core.config import get_settings

logger = logging.getLogger(__name__)

class AiAssessment(BaseModel):
    document_valid: bool = Field(description="Is the document visually plausible for the claimed document type?")
    identity_consistent: bool = Field(description="Are the OCR, MRZ, and visible fields internally consistent?")
    tampering_concern: bool = Field(description="Does the forensic/ELA evidence support suspicion of tampering?")
    identity_match_status: Literal["verified", "mismatch", "inconclusive"] = Field(description="Visual biometric correspondence status.")
    inconclusive: bool = Field(description="True if evidence is conflicting or insufficient to make a firm decision.")
    risk_score: int = Field(ge=0, le=100, description="Overall risk score from 0 (lowest) to 100 (highest).")
    risk_level: Literal["low", "medium", "high", "critical"] = Field(description="Overall risk level.")
    decision: Literal["approve", "review", "reject"] = Field(description="Final decision.")
    risk_factors: list[str] = Field(default_factory=list, description="List of reasons for high risk or review.")
    reason: str = Field(description="Detailed internal reasoning of evidence consistency and contradictions.")
    report: str = Field(description="Formal concise human-readable screening summary based only on the evidence.")


class InputQualification(BaseModel):
    input_valid: bool = Field(description="True if both the document and face images are suitable for processing.")
    document_suitable: bool = Field(description="Is the document image readable and visually a valid identity document?")
    person_image_suitable: bool = Field(description="Is the face image a clearly visible human face suitable for biometrics?")
    document_type_guess: Optional[str] = Field(default=None, description="Best guess of document type (e.g., passport, id_card), or null if unsure.")
    reason: str = Field(description="Reason for qualification or disqualification.")


def _encode_image(image_bytes: bytes) -> str:
    return base64.b64encode(image_bytes).decode("utf-8")


def _call_gemini(prompt: str, images: list[bytes], schema: type[BaseModel], model_name: str = "gemini-3.6-flash") -> BaseModel:
    """Calls Gemini API and enforces the structured schema."""
    settings = get_settings()
    if not settings.gemini_api_key:
        raise ValueError("GEMINI_API_KEY is not configured.")

    client = genai.Client(api_key=settings.gemini_api_key)
    
    contents = [prompt]
    for img_bytes in images:
        contents.append(
            types.Part.from_bytes(
                data=img_bytes,
                mime_type="image/jpeg",
            )
        )

    response = client.models.generate_content(
        model=model_name,
        contents=contents,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=schema,
            temperature=0.1,
        ),
    )
    
    # Parse the structured JSON output
    return schema.model_validate_json(response.text)


def _call_gemma_vision(prompt: str, images: list[bytes], schema: type[BaseModel], operation: str = "unknown") -> BaseModel:
    """Calls Google AI Studio Native REST API for gemma-4-31b-it."""
    settings = get_settings()
    if not settings.gemini_api_key:
        raise ValueError("GEMINI_API_KEY is not configured.")
        
    api_url = f"https://generativelanguage.googleapis.com/v1beta/models/gemma-4-31b-it:generateContent?key={settings.gemini_api_key}"
    
    import json
    json_schema = schema.model_json_schema()
    prompt_modifier = (
        f"\n\nCRITICAL INSTRUCTION: You MUST output ONLY a valid JSON object. "
        f"Do NOT output any conversational text, reasoning, or markdown formatting. "
        f"Output nothing but the JSON object."
    )
    
    parts = [{"text": prompt + prompt_modifier}]
    for img_bytes in images:
        b64_image = _encode_image(img_bytes)
        parts.append({
            "inlineData": {
                "mimeType": "image/jpeg",
                "data": b64_image
            }
        })
        
    payload = {
        "contents": [{"parts": parts}],
        "generationConfig": {
            "temperature": 0.1,
            "responseMimeType": "application/json",
            "responseSchema": json_schema
        }
    }
    
    headers = {"Content-Type": "application/json"}
    
    import time
    max_retries = 1
    for attempt in range(max_retries + 1):
        try:
            start_time = time.time()
            logger.info(f"[AI] Gemma START operation={operation} attempt={attempt+1}")
            
            with httpx.Client(timeout=60.0) as client:
                response = client.post(api_url, headers=headers, json=payload)
                
            duration_ms = int((time.time() - start_time) * 1000)
            
            if response.status_code == 200:
                logger.info(f"[AI] Gemma END operation={operation} duration={duration_ms}ms status=200 success=True")
                response_data = response.json()
                
                try:
                    candidates = response_data.get("candidates", [])
                    if not candidates:
                        raise ValueError(f"No candidates returned: {response_data}")
                    content_parts = candidates[0].get("content", {}).get("parts", [])
                    if not content_parts:
                        raise ValueError(f"No parts in content: {response_data}")
                    
                    result_text = content_parts[0].get("text", "")
                    
                    print(f"\n--- GEMMA RAW OUTPUT ({operation}) ---")
                    print(result_text)
                    print("--------------------------------------\n")
                    
                    # Clean markdown and extract JSON
                    # Find the first { and last } unconditionally to strip any prefix/suffix garbage
                    start_idx = result_text.find("{")
                    end_idx = result_text.rfind("}")
                    if start_idx != -1 and end_idx != -1 and end_idx >= start_idx:
                        result_text = result_text[start_idx:end_idx+1]
                    else:
                        raise ValueError(f"Could not find JSON object in response")
                    
                    return schema.model_validate_json(result_text)
                except Exception as e:
                    logger.error(f"[AI] Gemma PARSE ERROR: {e}")
                    raise ValueError(f"Failed to parse Gemma output: {e}")
                    
            status = response.status_code
            error_body = response.text
            
            if status == 400:
                logger.error(f"[AI] Gemma END operation={operation} duration={duration_ms}ms status=400 failure_category=REQUEST_FORMAT_PROBLEM error={error_body}")
                raise ValueError(f"Gemma 400 Bad Request (FATAL): {error_body}")
            elif status in (401, 403):
                logger.error(f"[AI] Gemma END operation={operation} duration={duration_ms}ms status={status} failure_category=AUTH_PROBLEM error={error_body}")
                raise ValueError(f"Gemma Auth Error (FATAL): {error_body}")
            elif status == 429:
                logger.error(f"[AI] Gemma END operation={operation} duration={duration_ms}ms status=429 failure_category=RATE_LIMIT error={error_body}")
                if attempt < max_retries:
                    time.sleep(2)
                    continue
                raise RuntimeError("Gemma 429 Rate Limit (RETRY EXHAUSTED)")
            elif status in (500, 503):
                logger.error(f"[AI] Gemma END operation={operation} duration={duration_ms}ms status={status} failure_category=SERVER_ERROR error={error_body}")
                if attempt < max_retries:
                    time.sleep(2)
                    continue
                raise RuntimeError(f"Gemma Server Error {status} (RETRY EXHAUSTED)")
            else:
                logger.error(f"[AI] Gemma END operation={operation} duration={duration_ms}ms status={status} failure_category=UNKNOWN_HTTP_ERROR error={error_body}")
                raise RuntimeError(f"Gemma HTTP {status}")
                
        except httpx.TimeoutException as e:
            duration_ms = int((time.time() - start_time) * 1000)
            logger.error(f"[AI] Gemma END operation={operation} duration={duration_ms}ms status=TIMEOUT failure_category=TIMEOUT error={str(e)}")
            if attempt < max_retries:
                continue
            raise RuntimeError("Gemma Timeout (RETRY EXHAUSTED)")
        except httpx.RequestError as e:
            duration_ms = int((time.time() - start_time) * 1000)
            logger.error(f"[AI] Gemma END operation={operation} duration={duration_ms}ms status=NETWORK_ERROR failure_category=NETWORK_ERROR error={str(e)}")
            if attempt < max_retries:
                time.sleep(1)
                continue
            raise RuntimeError(f"Gemma Network Error (RETRY EXHAUSTED): {str(e)}")

    raise RuntimeError("Gemma request failed")


def _call_openrouter(prompt: str, images: list[bytes], schema: type[BaseModel]) -> BaseModel:
    """Calls OpenRouter API using OpenAI-compatible payload."""
    settings = get_settings()
    if not settings.openrouter_api_key:
        raise ValueError("OPENROUTER_API_KEY is not configured.")

    headers = {
        "Authorization": f"Bearer {settings.openrouter_api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "http://localhost:8000",
        "X-Title": "VeriGate"
    }
    
    content = [{"type": "text", "text": prompt}]
    for img_bytes in images:
        b64_image = _encode_image(img_bytes)
        content.append({
            "type": "image_url",
            "image_url": {
                "url": f"data:image/jpeg;base64,{b64_image}"
            }
        })

    payload = {
        "model": settings.openrouter_model,
        "messages": [
            {
                "role": "user",
                "content": content
            }
        ],
        "temperature": 0.1,
        "response_format": {
            "type": "json_schema",
            "json_schema": {
                "name": schema.__name__,
                "schema": schema.model_json_schema(),
                "strict": True
            }
        }
    }

    with httpx.Client(timeout=45.0) as client:
        response = client.post("https://openrouter.ai/api/v1/chat/completions", headers=headers, json=payload)
        response.raise_for_status()
        
    response_data = response.json()
    if "choices" not in response_data or not response_data["choices"]:
        raise ValueError(f"Invalid response from OpenRouter: {response_data}")
        
    result_text = response_data["choices"][0]["message"].get("content")
    if not result_text:
        raise ValueError("Empty content from OpenRouter")
        
    return schema.model_validate_json(result_text)


def _call_local_ai(prompt: str, images: list[bytes], schema: type[BaseModel]) -> BaseModel:
    """Fallback to the local AI provider."""
    settings = get_settings()
    if not settings.local_ai_api_url:
        raise ValueError("LOCAL_AI_API_URL is not configured.")

    # Use OpenAI-compatible chat completions endpoint
    headers = {
        "Content-Type": "application/json",
    }
    
    content = [{"type": "text", "text": prompt}]
    for img_bytes in images:
        b64_image = _encode_image(img_bytes)
        content.append({
            "type": "image_url",
            "image_url": {
                "url": f"data:image/jpeg;base64,{b64_image}"
            }
        })

    payload = {
        "model": settings.local_ai_model or "local-model",
        "messages": [
            {
                "role": "user",
                "content": content
            }
        ],
        "temperature": 0.1,
        "response_format": {
            "type": "json_schema",
            "json_schema": {
                "name": schema.__name__,
                "schema": schema.model_json_schema(),
                "strict": True
            }
        }
    }
    
    api_url = settings.local_ai_api_url
    if not api_url.endswith("/chat/completions"):
        api_url = f"{api_url.rstrip('/')}/chat/completions"

    with httpx.Client(timeout=120.0) as client:
        response = client.post(api_url, headers=headers, json=payload)
        response.raise_for_status()
        
    response_data = response.json()
    if "choices" not in response_data or not response_data["choices"]:
        raise ValueError(f"Invalid response from Local AI: {response_data}")
        
    result_text = response_data["choices"][0]["message"].get("content")
    if not result_text:
        raise ValueError("Empty content from Local AI")
        
    return schema.model_validate_json(result_text)


def _call_ollama_vision(prompt: str, images: list[bytes], schema: type[BaseModel], operation: str = "unknown") -> BaseModel:
    """Calls Ollama API with images and parses the result."""
    settings = get_settings()
    if not settings.vision_base_url:
        raise ValueError("VISION_BASE_URL is not configured.")
        
    headers = {
        "Content-Type": "application/json"
    }
    if settings.vision_api_key:
        headers["Authorization"] = f"Bearer {settings.vision_api_key}"
        
    images_b64 = []
    
    import io
    try:
        from PIL import Image
    except ImportError:
        Image = None

    print(f"\n--- OLLAMA VISION DEBUG: {operation} ---")
    print(f"Model: {settings.vision_model}")
    print(f"Timeout: {settings.vision_timeout_seconds}s")
    print(f"Stream: False")
    print(f"Prompt length: {len(prompt)} chars")
    print(f"Image count: {len(images)}")
    
    for i, img_bytes in enumerate(images):
        b64_str = _encode_image(img_bytes)
        images_b64.append(b64_str)
        
        # Debug logging for image properties
        size_bytes = len(img_bytes)
        b64_size = len(b64_str)
        dimensions = "unknown"
        if Image:
            try:
                img = Image.open(io.BytesIO(img_bytes))
                dimensions = f"{img.size[0]}x{img.size[1]}"
            except Exception:
                dimensions = "parse_error"
                
        print(f"  Image {i+1}: file_size={size_bytes}B, b64_size={b64_size}B, dimensions={dimensions}")
    print("-------------------------------------------\n")

    payload = {
        "model": settings.vision_model,
        "messages": [
            {
                "role": "user",
                "content": prompt,
                "images": images_b64
            }
        ],
        "stream": False
    }
    
    api_url = settings.vision_base_url
    if not api_url.endswith("/api/chat"):
        api_url = f"{api_url.rstrip('/')}/api/chat"

    import time
    start_time = time.time()
    logger.info(f"[AI] Ollama START operation={operation} timeout={settings.vision_timeout_seconds}s model={settings.vision_model}")
    print(f"[AI] Ollama START operation={operation} timeout={settings.vision_timeout_seconds}s model={settings.vision_model}")

    try:
        with httpx.Client(timeout=settings.vision_timeout_seconds) as client:
            response = client.post(api_url, headers=headers, json=payload)
            response.raise_for_status()
    except httpx.HTTPError as e:
        end_time = time.time()
        duration_ms = int((end_time - start_time) * 1000)
        status_code = getattr(e.response, "status_code", "N/A") if hasattr(e, "response") and e.response else "N/A"
        
        response_body = ""
        if hasattr(e, "response") and e.response:
            try:
                response_body = e.response.text
            except Exception:
                pass
                
        # Classify the error type based on status code
        error_type = "HTTP_ERROR"
        if status_code == 400:
            error_type = "REQUEST_FORMAT_PROBLEM (400)"
        elif status_code == 404:
            error_type = "ENDPOINT_PATH_PROBLEM (404)"
        elif status_code == 500:
            error_type = "OLLAMA_MODEL_ERROR (500)"
        elif status_code == 524:
            error_type = "CLOUDFLARE_TIMEOUT (524)"
                
        logger.error(f"[AI] Ollama END operation={operation} duration={duration_ms}ms status={status_code} success=False failure_category={error_type} error={str(e)} body={response_body}")
        print(f"[AI] Ollama END operation={operation} duration={duration_ms}ms status={status_code} success=False failure_category={error_type} error={str(e)} body={response_body}")
        raise
    except Exception as e:
        end_time = time.time()
        duration_ms = int((end_time - start_time) * 1000)
        logger.error(f"[AI] Ollama END operation={operation} duration={duration_ms}ms status=N/A success=False failure_category=UNKNOWN_ERROR error={str(e)}")
        print(f"[AI] Ollama END operation={operation} duration={duration_ms}ms status=N/A success=False failure_category=UNKNOWN_ERROR error={str(e)}")
        raise
        
    end_time = time.time()
    duration_ms = int((end_time - start_time) * 1000)
    
    logger.info(f"[AI] Ollama END operation={operation} duration={duration_ms}ms status={response.status_code} success=True")
    print(f"[AI] Ollama END operation={operation} duration={duration_ms}ms status={response.status_code} success=True")
        
    response_data = response.json()
    if "message" not in response_data or "content" not in response_data["message"]:
        raise ValueError(f"Invalid response from Ollama Vision: {response_data}")
        
    result_text = response_data["message"].get("content")
    if not result_text:
        raise ValueError("Empty content from Ollama Vision")
        
    result_text = result_text.strip()
    if result_text.startswith("```json"):
        result_text = result_text[7:]
    elif result_text.startswith("```"):
        result_text = result_text[3:]
    if result_text.endswith("```"):
        result_text = result_text[:-3]
    result_text = result_text.strip()
        
    return schema.model_validate_json(result_text)


def _call_ai_provider(prompt: str, images: list[bytes], schema: type[BaseModel], operation: str = "unknown") -> tuple[BaseModel, str]:
    """Tries Gemma first, falls back to Ollama, OpenRouter, then Local AI."""
    
    # 1. Try Gemma
    try:
        result = _call_gemma_vision(prompt, images, schema, operation=operation)
        return result, "gemma"
    except ValueError as ve:
        # 400 or auth errors are fatal, do not fallback to avoid propagating bad payloads or disguising config issues
        logger.error(f"Gemma API Fatal Error (NO FALLBACK): {ve}")
        raise ve
    except Exception as gemma_e:
        logger.warning(f"Gemma Vision API failed: {gemma_e}. Attempting Ollama fallback.")
        
    # 2. Try Ollama Vision
    try:
        result = _call_ollama_vision(prompt, images, schema, operation=operation)
        return result, "ollama"
    except Exception as ollama_e:
        logger.warning(f"Ollama Vision API failed: {ollama_e}. Attempting OpenRouter fallback.")
        
    # 3. Try OpenRouter
    try:
        result = _call_openrouter(prompt, images, schema)
        return result, "openrouter"
    except Exception as openrouter_e:
        logger.error(f"OpenRouter API failed: {openrouter_e}.")
        raise RuntimeError("All AI providers failed.")


def qualify_inputs(document_bytes: bytes, face_bytes: bytes) -> InputQualification:
    """Validates if both the document and face images are suitable before processing."""
    prompt = (
        "Inspect the provided images (Image 1: document, Image 2: presented person). "
        "1. Does Image 1 appear to be a valid identity or travel document (like a passport, ID card, or visa) and is it sufficiently visible and readable? "
        "2. Is Image 2 a clearly visible human face suitable for biometric comparison? "
        "If either image is an obvious unrelated object (e.g., a tree, a train, screenshot of a website) or completely unreadable, mark input_valid as false. "
        "GLOBAL CONTEXT: Documents labeled `VERIGATE / SYNTHETIC IDENTITY LAB` are authorized synthetic documents created specifically for VeriGate software testing. "
        "Treat these documents as valid test documents for the purpose of this evaluation. Do not reject them merely because they are fictional, synthetic, or not government-issued. "
        "Evaluate their fields, consistency, tampering, and face match normally. Reject/review them only when actual evidence indicates an error, inconsistency, tampering, invalid field, or identity mismatch. "
        "IMPORTANT: You MUST return ONLY valid JSON. Your JSON MUST contain EXACTLY these keys: "
        '"input_valid" (boolean), "document_suitable" (boolean), "person_image_suitable" (boolean), '
        '"document_type_guess" (string or null), "reason" (string). '
        'Do not include markdown code blocks or any other text.'
    )
    try:
        result, _ = _call_ai_provider(prompt, [document_bytes, face_bytes], InputQualification, operation="input_qualification")
        return result
    except Exception as e:
        logger.error(f"Input qualification failed: {e}")
        # If AI fails at the gate, we fail open to let the pipeline attempt it.
        return InputQualification(
            input_valid=True, 
            document_suitable=True, 
            person_image_suitable=True,
            reason="AI qualification unavailable, proceeding by default."
        )


def _generate_inconclusive_assessment(reason: str) -> AiAssessment:
    """Generates a failsafe inconclusive assessment when models fail."""
    return AiAssessment(
        document_valid=False,
        identity_consistent=False,
        tampering_concern=False,
        identity_match_status="inconclusive",
        inconclusive=True,
        risk_score=50,
        risk_level="high",
        decision="review",
        reason=reason,
        report="AI reasoning service is currently unavailable. Please connect the configured local model or try again.",
        risk_factors=[]
    )


def assess_evidence(
    document_image: bytes,
    face_image: Optional[bytes],
    tampering_image: Optional[bytes],
    ocr_data: dict,
    mrz_data: dict,
    validation_data: list,
    tampering_data: dict,
    face_data: dict,
    temporal_data: dict = None
) -> tuple[AiAssessment, Optional[AiAssessment], Optional[AiAssessment], str]:
    """
    Main Reasoning Layer: Analyzes all evidence and images.
    Performs double-run consistency checking.
    Returns (final_assessment, run1, run2, ai_provider).
    """
    temporal_data_str = json.dumps(temporal_data) if temporal_data else "{}"

    prompt = f"""
You are the central reasoning layer for an identity document screening system.
Analyze the provided images and the objective evidence collected by lower-level tools.

EVIDENCE:
OCR Data: {json.dumps(ocr_data)}
MRZ Data: {json.dumps(mrz_data)}
Validation Checks: {json.dumps(validation_data)}
Temporal & Age Data (HARD FACTS): {temporal_data_str}
Tampering Analysis: {json.dumps(tampering_data)}
Face Verification (Distance/Match): {json.dumps(face_data)}

GLOBAL CONTEXT:
Documents labeled `VERIGATE / SYNTHETIC IDENTITY LAB` are authorized synthetic documents created specifically for VeriGate software testing. Treat these documents as valid test documents for the purpose of this evaluation. Do not reject them merely because they are fictional, synthetic, or not government-issued. Evaluate their fields, consistency, tampering, and face match normally. Reject/review them only when actual evidence indicates an error, inconsistency, tampering, invalid field, or identity mismatch.

INSTRUCTIONS:
1. Compare the visible fields in the document image with the OCR and MRZ data.
2. Evaluate if the tampering evidence meaningfully supports suspicion.
3. Review the face verification match evidence and visually confirm if the document face matches the presented face.
4. Check for any contradictions (e.g., MRZ invalid, mismatching names, face threshold exceeded).
5. IMPORTANT EVIDENCE RULE: NEVER fabricate biometric matching. If DeepFace verification evidence is missing or errored, you MUST set identity_match_status to "inconclusive", inconclusive to true, and decision to "review". Objective facts remain objective facts.
6. HARD FACTS RULE (TEMPORAL/AGE): You MUST strictly obey the temporal data. 
    - A `null` value for issue or expiry dates simply means the field was not available in the document, NOT that validation failed. Do NOT mark the document invalid solely because issue or expiry is missing, unless that particular document type explicitly requires it.
    - If `dob_in_future` is true, the document is mathematically invalid.
    - If `document_expired` is true, the document is expired and invalid.
    - If `issue_in_future` is true, the document is invalid.
    - If `issue_before_expiry` is false, the document dates are illogical.
    - Apply validation ONLY when the corresponding dates actually exist.
    - Use `calculated_age` as supporting evidence when comparing the document identity information with the presented person visually. Do NOT invent an exact visual age. If there is a severe age discrepancy, consider it a risk and review/reject.
    - Under NO circumstances can you override these mathematical facts. Do NOT invent missing dates.
7. Provide a final risk score (0-100), risk level (low, medium, high, critical), and decision (approve, review, reject).
8. IMPORTANT: You MUST return ONLY valid JSON. Your JSON MUST contain EXACTLY these keys:
"document_valid" (boolean), "identity_consistent" (boolean), "tampering_concern" (boolean), 
"identity_match_status" (string: "verified", "mismatch", or "inconclusive"), "inconclusive" (boolean),
"risk_score" (integer 0-100), "risk_level" (string: "low", "medium", "high", "critical"),
"decision" (string: "approve", "review", "reject"), "risk_factors" (list of strings), 
"reason" (string), "report" (string).
Do not include markdown code blocks or any other text.
"""
    
    images = [document_image]
    if face_image:
        images.append(face_image)

    try:
        # Run 1
        run1, provider = _call_ai_provider(prompt, images, AiAssessment, operation="main_investigation")
        
        # Check if consistency run is configured
        settings = get_settings()
        if settings.ai_consistency_runs >= 2:
            # Run 2 (Consistency Check)
            run2, _ = _call_ai_provider(prompt, images, AiAssessment, operation="main_investigation_run2")

            # Consistency Verification
            if run1.decision != run2.decision or run1.risk_level != run2.risk_level:
                logger.warning(f"AI Consistency failure! Run 1: {run1.decision}/{run1.risk_level} | Run 2: {run2.decision}/{run2.risk_level}")
                return _generate_inconclusive_assessment("Material disagreement between AI reasoning runs."), run1, run2, provider
            
            return run1, run1, run2, provider
        else:
            return run1, run1, None, provider

    except Exception as e:
        logger.error(f"Assess evidence failed: {e}")
        return _generate_inconclusive_assessment("All AI providers failed."), None, None, "none"

