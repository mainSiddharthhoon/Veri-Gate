# Veri-Gate E2E Test Results

This artifact contains the results of running all the test fixtures located in the `testing-data/` folder against the VeriGate local verification pipeline.

---

## 🧪 Test: `valid/person1`

**Expected Outcome**: Here a man's 2 images and one documents are given , all things are valid and the document must be accepted with both photos and the output should be safe and riskfree.

**Actual Decision**: `APPROVE`
**Risk Level**: `LOW`
**Score**: 0/100

**Summary**: Synthetic test document verified. Identity fields are consistent, face match is confirmed, and no tampering detected.

**Match Result**: ✅ Logically Passed (Matched Expectation Category)

---

## 🧪 Test: `valid/person2`

**Expected Outcome**: Here a women's two images are given and her document is given , both of her images are different and all the given items are valid , the expected outcome must be valid and safe to move should come.

**Actual Decision**: `APPROVE`
**Risk Level**: `LOW`
**Score**: 0/100

**Summary**: Document verified as a valid synthetic test fixture. Identity is consistent across all fields, and biometric verification is successful. No risk factors identified.

**Match Result**: ✅ Logically Passed (Matched Expectation Category)

---

## ⚠️ Test: valid/person3
**Error**: Missing document or face image.

---

## ❌ Test: invalid/both-invalid
**Expected Outcome**: In the given image both images are not related to our verification process , so it must be denied.

**Error**: `OCR failed: {"detail":"Please provide a valid identity document and a clear photo of the person."}`

---

## 🧪 Test: `invalid/dates-invalid`

**Expected Outcome**: Here in the given images the document is expired in 2024 , so it should be denied.

**Actual Decision**: `APPROVE`
**Risk Level**: `LOW`
**Score**: 0/100

**Summary**: Document verified as an authorized synthetic test fixture. Identity is consistent across all fields, and biometric verification is successful. No tampering detected.

**Match Result**: ❌ Logical Mismatch

---

## 🧪 Test: `invalid/dates-invalid2`

**Expected Outcome**: In the given document the issued date is today 02/09/2026 , but in the expired date it's expired before issued , that's invalid, it must be denied or reviwed , expected outcome should be issue-expire date misconfiguration.

**Actual Decision**: `REJECT`
**Risk Level**: `CRITICAL`
**Score**: 95/100

**Summary**: Document rejected due to critical temporal inconsistencies: the issuance date (2026-09-02) occurs after the expiration date (2024-01-09), and the document is currently expired.

**Match Result**: ✅ Logically Passed (Matched Expectation Category)

---

## 🧪 Test: `invalid/dob-error`

**Expected Outcome**: In the given image the person's birthday is in future , that must be denied , expected outcome : birth in future .

**Actual Decision**: `REJECT`
**Risk Level**: `CRITICAL`
**Score**: 100/100

**Summary**: The identity document was rejected due to a critical temporal inconsistency: the date of birth (May 04, 2027) is in the future relative to the current date (September 02, 2026).

**Match Result**: ✅ Logically Passed (Matched Expectation Category)

---

## 🧪 Test: `invalid/gender-mismatch`

**Expected Outcome**: In the given image just there is small mistake in the person's gender on document , it maybe reviwied or denied, expected outcome , he is a male but on document it's a female.

**Actual Decision**: `APPROVE`
**Risk Level**: `LOW`
**Score**: 0/100

**Summary**: The synthetic identity document is valid for testing purposes. Identity fields are consistent, and biometric verification is successful. No risk factors identified.

**Match Result**: ❌ Logical Mismatch

---

## 🧪 Test: `invalid/multiple-errors`

**Expected Outcome**: This document carries multiple errors like birthdate,gender,issued date , name and the photo iteslef, expected outcome must be denied and should have shown this errors.

**Actual Decision**: `REJECT`
**Risk Level**: `CRITICAL`
**Score**: 95/100

**Summary**: Document rejected due to critical temporal inconsistencies (issue date after expiry date) and a complete biometric mismatch between the document photo and the presented individual.

**Match Result**: ✅ Logically Passed (Matched Expectation Category)

---

## 🧪 Test: `invalid/photo-mismatch`

**Expected Outcome**: Here in the given document there is a male and in the given image there is a female, the expected outcome is , in given image there a male and the given photo is of a female , gender mismatch , expected result fail or must review.

**Actual Decision**: `REJECT`
**Risk Level**: `CRITICAL`
**Score**: 100/100

**Summary**: Identity verification failed due to a critical biometric mismatch. The document photo (male) does not match the presented person (female).

**Match Result**: ✅ Logically Passed (Matched Expectation Category)

---

