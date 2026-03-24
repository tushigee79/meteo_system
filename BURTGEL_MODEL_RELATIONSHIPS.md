# BURTGEL MODEL RELATIONSHIPS

БҮРТГЭЛ системийн Django model-уудын хоорондын харилцаа  
(Project: BURTGEL / meteo_system)

Framework: Django ORM

---

# 1. Overview

Энэ файл нь системийн гол model-уудын хоорондын:

• ForeignKey  
• OneToOne  
• OneToMany  
• Lifecycle history relationships  

зэрэг холбоог тайлбарлана.

---

# 2. Core model groups

Model-ууд дараах үндсэн бүлэгт хуваагдана.

### Geographic models
Aimag  
SumDuureg  
Location  

### Core asset models
InstrumentCatalog  
Device  

### Lifecycle models
DeviceMovement  
MaintenanceService  
ControlAdjustment  
CalibrationRecord  
FailureIncident  

### User models
User (Django)  
UserProfile  

### Support models
Organization  
QRToken  
ManualLibraryItem  
SparePartOrder  
SparePartOrderItem  

---

# 3. Geographic hierarchy

```text
Aimag
  │
  └── SumDuureg
          │
          └── Location
                 │
                 └── Device

Relationships

Aimag → SumDuureg
OneToMany

SumDuureg → Location
OneToMany

Location → Device
OneToMany

4. Location relationships

Location нь системийн төв entity-ийн нэг.

Location
  ├── Organization
  ├── Aimag
  ├── SumDuureg
  └── Device

Django example

class Location(models.Model):
    aimag = models.ForeignKey(Aimag)
    sum_duureg = models.ForeignKey(SumDuureg)
    organization = models.ForeignKey(Organization)
5. Device relationships

Device бол системийн хамгийн чухал entity.

Device
 ├── Location
 ├── Organization
 ├── InstrumentCatalog
 ├── DeviceMovement
 ├── MaintenanceService
 ├── ControlAdjustment
 ├── CalibrationRecord
 ├── FailureIncident
 └── QRToken
6. Device → InstrumentCatalog
InstrumentCatalog
        │
        └── Device

Relationship

InstrumentCatalog → Device
OneToMany

Example

catalog = models.ForeignKey(InstrumentCatalog)

Purpose

Device-ийг стандарт каталогтой холбох.

7. Device lifecycle relationships

Device-тэй холбоотой lifecycle model-ууд:

Device
 ├── DeviceMovement
 ├── MaintenanceService
 ├── ControlAdjustment
 ├── CalibrationRecord
 └── FailureIncident

Эдгээр нь:

Device → History tables

OneToMany relationship.

8. DeviceMovement relationship
Device
   │
   └── DeviceMovement
          ├── source_location
          ├── destination_location
          └── approved_by

Example

class DeviceMovement(models.Model):
    device = models.ForeignKey(Device)
    source_location = models.ForeignKey(Location)
    destination_location = models.ForeignKey(Location)

Purpose

Багажийн байршлын өөрчлөлтийн түүх.

9. MaintenanceService relationship
Device
   │
   └── MaintenanceService

Example

class MaintenanceService(models.Model):
    device = models.ForeignKey(Device)

Purpose

Засвар үйлчилгээний бүртгэл.

10. CalibrationRecord relationship
Device
   │
   └── CalibrationRecord
          │
          └── CalibrationLab

Example

class CalibrationRecord(models.Model):
    device = models.ForeignKey(Device)

Purpose

Калибровка, баталгаажуулалтын түүх.

11. ControlAdjustment relationship
Device
   │
   └── ControlAdjustment

Purpose

Хяналт, тохируулга.

12. FailureIncident relationship
Device
   │
   └── FailureIncident

Purpose

Эвдрэл, доголдлын бүртгэл.

13. User relationships

Django-гийн User model дээр domain profile холбох.

User
  │
  └── UserProfile

Example

class UserProfile(models.Model):
    user = models.OneToOneField(User)
14. UserProfile usage

UserProfile дараах model-уудтай холбоотой.

UserProfile
 ├── DeviceMovement
 ├── MaintenanceService
 ├── ControlAdjustment
 └── ApprovalWorkflow

Example

approved_by = models.ForeignKey(UserProfile)
15. Organization relationships
Organization
 ├── Location
 ├── Device
 └── UserProfile

Example

organization = models.ForeignKey(Organization)

Purpose

Харьяалал, ownership.

16. QRToken relationship
Device
  │
  └── QRToken

Example

class QRToken(models.Model):
    device = models.ForeignKey(Device)

Purpose

QR code lookup болон device passport.

17. SparePart relationships
SparePartOrder
   │
   └── SparePartOrderItem
            │
            └── Device

Example

order = models.ForeignKey(SparePartOrder)
device = models.ForeignKey(Device)

Purpose

Сэлбэг хэрэгслийн захиалга.

18. Manual library relationship
ManualLibraryItem
      │
      └── Device (optional)

Purpose

Гарын авлагын сан.

19. Full ERD overview
Aimag
  │
  └── SumDuureg
        │
        └── Location
              │
              ├── Device
              │      ├── InstrumentCatalog
              │      ├── DeviceMovement
              │      ├── MaintenanceService
              │      ├── ControlAdjustment
              │      ├── CalibrationRecord
              │      ├── FailureIncident
              │      └── QRToken
              │
              └── Organization

User
  │
  └── UserProfile
         │
         ├── DeviceMovement
         ├── MaintenanceService
         └── ControlAdjustment
20. Relationship summary
Model	Relationship
Aimag → SumDuureg	OneToMany
SumDuureg → Location	OneToMany
Location → Device	OneToMany
InstrumentCatalog → Device	OneToMany
Device → MaintenanceService	OneToMany
Device → DeviceMovement	OneToMany
Device → CalibrationRecord	OneToMany
Device → ControlAdjustment	OneToMany
Device → FailureIncident	OneToMany
Device → QRToken	OneToMany
User → UserProfile	OneToOne
Organization → Location	OneToMany
21. Future model relationships

Ирээдүйд дараах entity нэмэгдэх боломжтой.

SystemAsset
SystemComponent
WorkflowAction
AuditLog
LoginEvent

22. Key design principle

Системийн design дараах зарчим дээр тулгуурлана.

Device = Master entity
Lifecycle tables = History entities

Ингэснээр:

• audit trail хадгалагдана
• report хийх боломж нэмэгдэнэ
• device lifecycle бүрэн харагдана

END

