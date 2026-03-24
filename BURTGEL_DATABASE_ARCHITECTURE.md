# BURTGEL DATABASE ARCHITECTURE

ЦУОШГ – Багаж, станц, систем, калибровка, засвар, шилжилт хөдөлгөөний өгөгдлийн сангийн архитектур

Project: БҮРТГЭЛ (BURTGEL)  
Framework: Django ORM  
Current DB: SQLite (development)  
Future DB: PostgreSQL

---

# 1. Purpose

Энэ баримт нь БҮРТГЭЛ системийн өгөгдлийн сангийн үндсэн бүтэц, model-уудын харилцаа, lifecycle логик, integrity rule, future scaling чиглэлийг тодорхойлно.

Системийн гол зорилго:

- байршил бүртгэх
- багаж бүртгэх
- багажийн каталог удирдах
- калибровка хянах
- засвар хянах
- шилжилт хөдөлгөөний түүх хадгалах
- QR / passport үүсгэх
- role-based access хэрэгжүүлэх
- WMO / OSCAR metadata-д нийцэх

---

# 2. Database design principles

Системийн өгөгдлийн сан дараах зарчмыг баримтална:

1. Master data ба transaction/history data-г салгаж хадгалах
2. Device lifecycle-ийн түүхэн мөрийг устгахгүй
3. Reference lookup table ашиглах
4. Role-based ownership ба visibility дэмжих
5. Future integration-д бэлэн байх
6. Export/report-д тохиромжтой normalized бүтэцтэй байх
7. Шаардлагатай хэсэгт denormalized summary field зөвшөөрөх

---

# 3. High-level entity groups

Өгөгдлийн сангийн entity-үүдийг дараах бүлэгт ангилна.

## 3.1 Reference / lookup entities
- Aimag
- SumDuureg
- Organization
- InstrumentCatalog
- CalibrationLab
- Manufacturer
- DeviceKind / Category
- Status lookup tables

## 3.2 Core master entities
- Location
- Device
- SystemAsset (future)
- UserProfile

## 3.3 Lifecycle / transactional entities
- DeviceMovement
- MaintenanceService
- ControlAdjustment
- CalibrationRecord
- FailureIncident
- SparePartOrder
- SparePartOrderItem

## 3.4 Access / audit entities
- QRToken
- AuditLog
- LoginEvent
- ApprovalWorkflow
- WorkflowAction

## 3.5 Documents / knowledge entities
- ManualLibraryItem
- DeviceAttachment
- StandardDocument

---

# 4. Core ERD overview

Ерөнхий харилцааны зураглал:

```text
Aimag ──< SumDuureg ──< Location ──< Device
                                │
                                ├──< DeviceMovement
                                ├──< MaintenanceService
                                ├──< ControlAdjustment
                                ├──< CalibrationRecord
                                ├──< FailureIncident
                                ├──< DeviceAttachment
                                └──< QRToken

InstrumentCatalog ──< Device
Organization ──< Location
Organization ──< Device
User ──1 UserProfile
UserProfile ──< DeviceMovement (approved_by / moved_by)
UserProfile ──< MaintenanceService
UserProfile ──< ControlAdjustment
CalibrationLab ──< CalibrationRecord
Device ──< SparePartUsage
SparePartOrder ──< SparePartOrderItem

5. Geographic / administrative hierarchy
5.1 Aimag

Аймаг/хотын master table

Suggested fields:

id

name

code

region

is_active

created_at

updated_at

Constraints:

name unique

code unique if available

5.2 SumDuureg

Сум/дүүргийн master table

Suggested fields:

id

aimag (FK → Aimag)

name

code

district_type

is_active

created_at

updated_at

Constraints:

unique together: (aimag, name)

Notes:

Улаанбаатарын дүүргүүд мөн энэ table-д орж болно

district_name-ийг тусдаа text биш FK-гаар холбох нь зөв

6. Organization model

System ownership, харьяалал, лаборатори, төв байгууллага, аймаг, УЦУОШТ зэрэг бүтцийг тодорхойлоход хэрэглэнэ.

Suggested fields:

id

name

short_name

organization_type

parent (self FK)

aimag (nullable FK)

location (nullable FK)

is_active

created_at

updated_at

Use cases:

ЦУОШГ

БОХЗТ лаборатори

Аймгийн УЦУОШТ

Төв нэгж

Гэрээт засварын байгууллага

7. Location model

Станц, оффис, AWS байршил, радар байрлал, лаборатори, facility түвшний байршлын үндсэн entity.

Suggested fields:

id

name

code

location_type

aimag (FK)

sum_duureg (FK)

organization (FK)

latitude

longitude

elevation_m

address

station_code

wigos_id

is_active

installed_at

description

temp_siting_class

wind_siting_class

siting_description

created_at

updated_at

Constraints:

unique on wigos_id when not null

optional unique on station code depending on business rule

Notes:

location_type values: WEATHER, HYDRO, AWS, RADAR, AEROLOGY, LAB, OFFICE, OTHER

future map/report logic энэ model дээр төвлөрнө

8. InstrumentCatalog model

Багажийн ерөнхий төрлийн каталог. Device-ээс тусдаа master entity байна.

Suggested fields:

id

name

code

kind

manufacturer

model

measurement_parameter

unit

verification_cycle_months

default_service_interval_months

expected_lifetime_years

specification_json

is_active

created_at

updated_at

Use cases:

AWS sensor catalog

radar subsystem types

hydrology gauges

calibration devices

эталон багаж

Constraints:

unique together: (manufacturer, model, kind) where appropriate

Notes:

Device бүр catalog-тай FK-аар холбогдоно

“Бусад” тохиолдолд free text override хадгалж болно

9. Device model

Системийн хамгийн чухал master entity. Багаж, тоног төхөөрөмж, subsystem, asset зэргийг төлөөлнө.

Suggested fields:

id

inventory_code

serial_number

name

kind

catalog (FK → InstrumentCatalog)

location (FK → Location)

organization (FK → Organization)

status

lifecycle_status

owner_organization

assigned_organization

installed_date

commissioned_date

manufacturer_name_override

model_name_override

firmware_version

software_version

last_verification_date

next_verification_date

purchase_date

purchase_cost

funding_source

warranty_until

notes

is_active

archived_at

created_at

updated_at

Critical constraints:

serial_number unique where business rule requires

inventory_code unique

catalog nullable only if “Other” logic хэрэгжиж байвал

Recommended indexes:

serial_number

inventory_code

status

lifecycle_status

location

kind

next_verification_date

Notes:

Device table дээр одоогийн төлөв хадгална

History table-ууд дээр өөрчлөлтийн мөр хадгална

10. Device status model strategy

2 арга бий:

Option A: choices field

status, lifecycle_status-ийг choices field-р хадгалах

Pros:

хурдан

энгийн

Cons:

admin configurable биш

Option B: lookup table

DeviceStatus, LifecycleStatus table ашиглах

Pros:

уян хатан

config хийж болно

Cons:

бага зэрэг төвөгтэй

Recommended:

v1.0 дээр choices

v2.0 дээр lookup table руу шилжиж болно

11. DeviceMovement model

Багажийн байршлын өөрчлөлтийн түүх.

Suggested fields:

id

device (FK → Device)

source_location (FK → Location, nullable)

destination_location (FK → Location)

movement_date

reason

approved_by (FK → UserProfile, nullable)

moved_by (FK → UserProfile, nullable)

notes

document_number

created_at

updated_at

Rules:

Device.location өөрчлөгдөх үед DeviceMovement record заавал үүсэх

source_location = old location

destination_location = new location

Indexes:

device

movement_date

destination_location

12. MaintenanceService model

Засвар үйлчилгээ, гэмтэл арилгалт, үйлчилгээний бүртгэл.

Suggested fields:

id

device (FK → Device)

service_date

service_type

performed_by_type

engineer_name

organization_name

service_status

diagnosis

root_cause

action_taken

result_status

used_spare_parts_text

cost

next_service_due

attachment

notes

created_by

created_at

updated_at

Business logic:

performed_by_type = ENGINEER / ORGANIZATION

ENGINEER үед engineer_name бөглөнө

ORGANIZATION үед organization_name бөглөнө

Notes:

user-ийн хүссэн conditional input logic-ийг энд хэрэгжүүлнэ

13. ControlAdjustment model

Хяналт, тохируулга, шалгалтын бүртгэл.

Suggested fields:

id

device (FK → Device)

adjustment_date

adjustment_type

before_state

after_state

result

adjusted_by

organization_name

notes

created_at

updated_at

Use cases:

station calibration check

device tuning

control/verification actions

14. CalibrationRecord model

Калибровка, баталгаажуулалтын тусдаа entity.

Suggested fields:

id

device (FK → Device)

calibration_date

valid_until

calibration_type

lab_choice

lab_name_other

certificate_number

result

uncertainty

remarks

attachment

created_at

updated_at

Business logic:

lab_choice = CAL_LAB / OTHER

OTHER үед lab_name_other бөглөнө

Automation:

хадгалах үед Device.last_verification_date шинэчилнэ

Device.next_verification_date-г catalog.verification_cycle_months-аас тооцно

Indexes:

device

calibration_date

valid_until

15. FailureIncident model

Эвдрэл, доголдол, тасалдлын бүртгэл.

Suggested fields:

id

device (FK → Device)

incident_date

severity

failure_type

description

probable_cause

affected_operation

immediate_action

resolved_at

resolution_summary

created_at

updated_at

Use cases:

системийн тасалдал

AWS sensor failure

radar subsystem fault

etalon instrument damage

16. SparePartOrder and SparePartOrderItem
SparePartOrder

Suggested fields:

id

request_number

aimag

requested_by

requested_date

status

supplier

notes

created_at

updated_at

SparePartOrderItem

Suggested fields:

id

order (FK → SparePartOrder)

device (nullable FK)

part_name

part_type

serial_number

quantity

unit

remarks

Notes:

Аймгийн инженерийн эрхээр aimag auto-fill хийнэ

delete permission хязгаарлана

17. UserProfile model

User-тэй холбоотой domain profile.

Suggested fields:

id

user (OneToOne → auth.User)

full_name

phone

organization

aimag

role

position

must_change_password

is_active

created_at

updated_at

Main use:

Aimag engineer restriction

queryset filtering

workflow approval

audit log

18. QRToken model

Public QR lookup болон device passport access-д хэрэглэнэ.

Suggested fields:

id

device (FK → Device)

token (UUID, unique)

is_active

issued_at

revoked_at

expires_at

created_by

notes

Rules:

active token 1 эсвэл business rule-аас шалтгаалж олон байж болно

revoke хийхэд is_active=False

Indexes:

token

device

is_active

19. AuditLog model

Чухал үйлдлийн audit trail.

Suggested fields:

id

user

action_type

content_type

object_id

object_repr

before_json

after_json

ip_address

timestamp

success

notes

Use cases:

login / logout

create / update / delete attempt

status change

QR revoke

approval action

20. ManualLibraryItem model

Гарын авлагын сангийн entity.

Suggested fields:

id

title

category

topic

instrument_kind

manufacturer

document_type

file

external_url

published_date

is_archived

description

created_at

updated_at

Use cases:

PDF

DOCX

image

video

standards

training material

21. DeviceAttachment model

Device-тэй холбоотой хавсралтууд.

Suggested fields:

id

device (FK → Device)

attachment_type

file

title

description

uploaded_by

created_at

Use cases:

паспорт

зураг

сертификат

акт

засварын тайлан

22. System-level asset extension (future)

Ирээдүйд радар, аэрологи, AWS станц зэрэг facility-level системд дараах загвар хэрэгтэй байж болно.

SystemAsset

id

name

system_type

location

organization

status

lifecycle_status

commissioned_date

notes

SystemComponent

id

system_asset (FK)

device (FK)

component_role

installed_at

removed_at

is_active

Энэ загвар нь:

radar as system

radar transmitter as device

radome as component

UPS as component

network switch as component

гэж ялгаж бүртгэх боломж өгнө.

23. Device Passport data assembly

Device Passport PDF хийхэд дараах entity-үүдээс өгөгдөл татна:

Device

Location

InstrumentCatalog

CalibrationRecord (last)

MaintenanceService (last 5)

DeviceMovement (recent)

QRToken (active)

siting info from Location

Иймээс passport generation нь reporting layer боловч database design-д сайн index хэрэгтэй.

24. Key integrity rules
24.1 Device

serial_number давхцахгүй

inventory_code давхцахгүй

24.2 Location

aimag, sum_duureg consistency шалгана

UB district зөв aimag-д харьяалагдах ёстой

24.3 UserProfile

AimagEngineer role бол aimag заавал бөглөгдсөн байна

24.4 Calibration

valid_until >= calibration_date

OTHER lab үед lab_name_other required

24.5 Maintenance

performed_by_type дээр conditional validation

24.6 Device movement

source_location ≠ destination_location

movement_date required

25. Query / reporting optimization

Тайлан их гарах тул дараах optimization саналтай.

Index-heavy fields

Device.serial_number

Device.inventory_code

Device.status

Device.lifecycle_status

Device.location_id

Device.kind

Device.next_verification_date

Location.aimag_id

Location.location_type

DeviceMovement.movement_date

CalibrationRecord.valid_until

Useful annotations

device count by organization

device count by aimag

verification bucket counts

maintenance counts by period

overdue verification count

Denormalized optional fields

Device.current_verification_bucket

Location.device_count_cache

Organization.device_count_cache

Эдгээрийг зөвхөн performance шаардлагатай үед нэмнэ.

26. Migration strategy

Төслийн migration instability-ийг багасгахын тулд:

Нэг дор олон branch migration бүү үүсгэ

Master branch дээр squash хийх

Production-ready болохоос өмнө dependency clean хий

Data migration ба schema migration-ийг тусад нь байлга

Reference import command-уудаар seed data оруул

Recommended naming:

00xx_add_device_passport_fields

00xx_add_device_movement

00xx_backfill_location_org

00xx_add_wigos_id_to_location

27. Security-related DB design

Security шаардлагад:

OTP / temporary password sent flag

must_change_password

login failure count

last_login_ip

AuditLog

LoginEvent

гэнэ.

Optional models:

LoginEvent

user

login_time

ip_address

success

user_agent

28. WMO / OSCAR alignment fields

Future compliance-д дараах талбарууд хэрэгтэй.

Location

wigos_id

station_program

observing_practice

siting_class fields

Device

observed_variable

observation_method

calibration_cycle

traceability_info

DeviceMovement

relocation reason

metadata change reference

29. Suggested implementation order
Phase 1 – stability

Aimag

SumDuureg

Organization

Location

InstrumentCatalog

Device

UserProfile

Phase 2 – lifecycle

CalibrationRecord

MaintenanceService

DeviceMovement

ControlAdjustment

FailureIncident

Phase 3 – operations

QRToken

AuditLog

SparePartOrder

SparePartOrderItem

ManualLibraryItem

Phase 4 – advanced

SystemAsset

SystemComponent

ApprovalWorkflow

WorkflowAction

LoginEvent

30. Admin mapping

Database entity → admin module mapping:

Location → location admin

Device → device admin

InstrumentCatalog → catalog admin

CalibrationRecord → calibration admin / inline

MaintenanceService → maintenance admin / inline

DeviceMovement → movement inline

QRToken → actions / token admin

AuditLog → readonly admin

ManualLibraryItem → manual library admin

31. Recommended future admin/package structure
inventory/
    models.py
    admin/
        admin_site.py
        admin_devices.py
        admin_locations.py
        admin_calibration.py
        admin_maintenance.py
        admin_reports.py
        admin_qr.py
        admin_manuals.py

Ингэснээр DB architecture ба admin architecture хооронд ойлгомжтой холбоо үүснэ.

32. Summary

БҮРТГЭЛ системийн өгөгдлийн сангийн цөм нь:

Location

Device

InstrumentCatalog

UserProfile

гэсэн master entity-үүд дээр тогтож,

DeviceMovement

MaintenanceService

CalibrationRecord

ControlAdjustment

FailureIncident

гэсэн lifecycle/history entity-үүдээр өргөжнө.

Цаашид:

QR/passport

reporting

audit

workflow

system-level assets

WMO/OSCAR metadata

гэсэн чиглэлээр томорч үндэсний хэмжээний платформ болох боломжтой.

END

---

Одоо танай documentation stack ийм боллоо:

```text
AI_MEMORY.md
PROJECT_CONTEXT.md
PROJECT_INDEX.md
BUGS_AND_PATCHES.md
DEV_WORKFLOW.md
BURTGEL_SYSTEM_ARCHITECTURE.md
BURTGEL_DATABASE_ARCHITECTURE.md