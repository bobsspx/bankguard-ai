# BankGuard AI — Phase 5F.1 Step 1

สถานะ: ✅ COMPLETED เฉพาะ pure feature extraction + unit tests
สถานะทั้ง Phase: ❌ FIX REQUIRED — ยังต้องตรวจใน repository เต็ม

## ผลตรวจ source ที่ได้รับ

ZIP ต้นฉบับมี 51 ไฟล์: models, services, schemas, API, tests และ migration versions.
ไม่มี app/db, app/core, app/main.py, dependency manifest/lockfile, alembic.ini,
alembic/env.py หรือ frontend. ไม่มี feature extraction เดิมในชุดนี้.
จึงไม่สามารถสรุปว่า repository จริงไม่มีโมดูล ML หรือ dependencies ดังกล่าว.

Transaction มี id, account_id, device_id, amount, currency, transaction_type,
merchant_category, country_code, channel, ip_address, status, occurred_at, created_at.
Account มี country_code และ currency แต่ไม่มี historical profile versions.
Device มี trusted, first_seen_at, last_seen_at แต่ไม่มี historical trust snapshots.
FraudScore มี ml_score อยู่แล้ว ไม่ต้องสร้างซ้ำ; fraud_scoring.py ปัจจุบันตั้ง
ml_score=0 และ model_version=rules-v1. ยังไม่มีการเชื่อม ML ใน patch นี้.
FraudDecision มี decision/reviewed_at สำหรับ labels ภายหลัง แต่ห้ามเป็น predictors.

Migration chain ใน ZIP:
ced71a58004e -> 0e8fe4580693 -> 03f84ae784f8 -> 51f90974f653 -> 0bed84b6e331.
นี่คือ head จากไฟล์ที่ได้รับ ไม่ใช่หลักฐานสถานะฐานข้อมูล Neon.

## ติดตั้ง: สร้างไฟล์ใหม่เท่านั้น

แตก ZIP นี้ไว้ในโฟลเดอร์ชั่วคราว จากนั้นคัดลอก:

| ไฟล์ใน ZIP | ตำแหน่งใน project | การเปลี่ยนแปลง |
| --- | --- | --- |
| backend/app/services/ml_features.py | backend/app/services/ml_features.py | สร้างไฟล์ใหม่ |
| backend/tests/test_ml_features.py | backend/tests/test_ml_features.py | สร้างไฟล์ใหม่ |
| docs/PHASE_5F1_README.md | docs/PHASE_5F1_README.md | สร้างไฟล์ใหม่ |

ไฟล์ Python เป็นโค้ดเต็ม พร้อมใช้ ไม่ต้องประกอบ snippets.
หากเครื่องคุณมีไฟล์ชื่อเดียวกันอยู่แล้ว ให้เปรียบเทียบก่อนคัดลอก เพราะ ZIP
ที่ส่งมาตรวจไม่มีไฟล์เหล่านี้. ไม่ต้องแทนที่โฟลเดอร์ backend ทั้งก้อน.
ไม่มีการแก้ไฟล์เดิม ไม่มี migration ไม่มี frontend changes ไม่มี dependency ใหม่.
Python ใช้ standard library; tests ใช้ pytest เดิมของ project.

## Feature contract

เรียก extract_transaction_features(transaction, history).
รับ Transaction ORM objects ที่โหลดมาแล้ว หรือ DTO ที่มี fields ตาม TransactionLike.
ฟังก์ชันไม่อ่าน database เอง. Caller ต้องส่งประวัติครบ 30 วันของบัญชีเดียวกัน.
อย่าใช้ history=[] กับรายการที่มีประวัติจริงเพียงเพื่อให้ฟังก์ชันรันได้.
ผลลัพธ์ FeatureRow เก็บ transaction_id และ feature_version เป็น metadata.
ใช้ row.as_dict() เป็น model inputs เท่านั้น (20 features ตาม FEATURE_NAMES).
ห้ามนำ transaction_id หรือ raw account/device/IP identifiers มาเป็น predictors.

- amount, currency, hour_utc, weekday_utc (Monday=0), channel,
  transaction_type, merchant_category, country_code.
- account_country_mismatch: None เว้นแต่ส่ง account_country_at_event
  ที่ตรวจสอบแล้วว่าเป็น snapshot ณ เวลาเกิดเหตุ. ห้ามส่งค่าปัจจุบันจาก Account
  เพื่ออ้างว่าเป็นข้อมูลย้อนหลังที่ป้องกัน leakage แล้ว.
- history_count_30d, recent_count_10m, recent_count_24h: นับทุก currency.
- same_currency_count_30d, mean_amount_30d, amount_to_mean_30d,
  recent_amount_24h: เฉพาะ currency เดียวกับ target; ไม่มี FX conversion.
- device_missing, ip_missing; device_unseen_30d, ip_unseen_30d:
  unknown=None เมื่อไม่มีประวัติค่าที่ใช้เปรียบเทียบได้ หรือ target ไม่มีค่านั้น.
  unseen หมายถึงไม่พบใน 30 วัน ไม่ได้หมายความว่าอุปกรณ์นั้นเป็นอันตราย.

Window คือ [occurred_at - duration, occurred_at). ตัด self, timestamp ที่เท่ากัน,
อนาคต, บัญชีอื่น และรายการที่ created_at > target.created_at.
Timestamp ต้องมี timezone และถูก normalize เป็น UTC.
ผลลัพธ์ไม่เปลี่ยนตามลำดับ history; duplicate eligible IDs ทำให้ error.
ไม่ใช้ status, fraud decision, alert status, reviewer, rule score หรือ device trust.
None ต้องถูกจัดการด้วย preprocessing ที่ fit เฉพาะ training partition ใน Phase 5F.3.
ยังไม่ทำ scaling/encoding/training เพื่อไม่ให้ข้าม Phase.

## ข้อจำกัดด้าน point-in-time correctness

created_at ใช้เป็น conservative proxy ของเวลาที่รายการพร้อมให้ระบบใช้.
ความถูกต้องย้อนหลังยังขึ้นอยู่กับ immutable transaction values และประวัติครบ.
Schema ที่ได้รับไม่มี version history สำหรับการแก้ไข transaction.
ถ้าธุรกรรมถูกแก้ย้อนหลัง หรือ import ข้อมูลโดยไม่รักษาเวลาที่ระบบรู้ข้อมูล
ต้องจัด immutable dataset snapshot และนโยบาย availability ก่อน training.
โค้ดนี้ป้องกัน temporal/outcome leakage ตาม contract แต่ไม่ได้รับประกันว่า
ฐานข้อมูลปัจจุบันสามารถ reconstruct ประวัติทั้งหมดได้โดยไม่มี leakage.
การเทียบ country ไม่ใช่การตรวจประเทศปลายทางการโอน เพราะ schema ไม่มี field นั้น.

## หลักฐานการทดสอบใน environment นี้

Python 3.12; pytest 9.1.1.
python -m pytest -q tests/test_ml_features.py tests/test_fraud_rules.py
ผล: 32 passed (24 ใหม่ + 8 Rule Engine เดิม).
python -m compileall -q app/services/ml_features.py tests/test_ml_features.py
ผล: exit 0.
python -m pytest -q
ผล: collection errors 6 modules: SQLAlchemy ไม่ได้ติดตั้ง และ app.core ไม่มีใน ZIP.
app.db ก็ไม่มีใน ZIP. ไม่ได้สร้าง stub แทนโค้ดเดิมหรือเอา tests ออกเพื่อให้ผ่าน.
ไม่ได้ทดสอบ DB, API integration, frontend หรือยืนยัน baseline 53 tests ใน environment นี้.
ML packages ใน environment นี้มีอยู่ แต่ไม่ใช่หลักฐานว่าเครื่องผู้ใช้ติดตั้งแล้ว.

## คำสั่งบน Windows PowerShell

```powershell
cd C:\Users\MSII\Desktop\porfolio\bankguard-ai\backend
.\.venv\Scripts\Activate.ps1
python -m pytest -q tests/test_ml_features.py
python -m pytest -q
alembic current
python -m pip show scikit-learn pandas numpy joblib
```

Expected: tests ใหม่ 24 passed; full suite ต้องไม่ลดจาก baseline เดิม.
ถ้า baseline คือ 53 tests จริง และไม่มีการเปลี่ยนจำนวนอื่น ควรได้ 77 passed.
alembic current ควรเป็น (head) ของ repository จริง. รอบนี้ไม่มี migration ใหม่
จึงไม่ต้องรัน alembic upgrade head เพื่อใช้ feature extractor.
หาก pip show ไม่พบ ML packages ให้บันทึกไว้สำหรับ dependency setup ใน Phase 5F.3;
ไม่จำเป็นต้องติดตั้งเพื่อรัน Phase 5F.1 นี้.
ไม่มี frontend changes จึงไม่ต้องรัน lint/build ใหม่สำหรับ patch นี้.

## ส่งหลักฐานกลับ 3 ภาพ

1. Terminal: tests/test_ml_features.py ได้ 24 passed.
2. Terminal: full pytest พร้อม summary และ errors หากมี.
3. Terminal: alembic current และ pip show ข้างต้น.

ส่ง dependency manifest/lockfile และ backend source ที่ขาด เพื่อให้ตรวจ full suite
และออกแบบ database query adapter ตาม session/config จริงได้. ไม่แนบ .env,
JWT secrets, DATABASE_URL, .venv, node_modules หรือข้อมูลลูกค้าจริง.

ขั้นถัดไปภายใน 5F.1: ตรวจ DB/session integration และ data availability ด้วย repo เต็ม.
เมื่อ quality gate ผ่านแล้วจึงไป 5F.2: reproducible synthetic labels + temporal split,
แยก synthetic labels จาก reviewer labels และห้ามให้ unlabeled = legitimate อัตโนมัติ.
