# Partscape — Strategic Blueprint
## Auto-Parts Intelligence System for Commonwealth of Dominica
### Native Frappe/ERPNext Custom App | Seityl Group Ltd.

**Version:** 1.0.0  
**Date:** 2026-05-24  
**Classification:** Strategic Architecture Document  
**Target Runtime:** Frappe v15+, Python 3.11+, MariaDB 10.6+

---

## 1. Executive Summary

This document blueprints **Partscape**, a native Frappe custom app that embeds automotive parts intelligence directly into ERPNext. The system targets the Commonwealth of Dominica's used-Japanese vehicle fleet (RHD, left-hand traffic, heavy import of JDM Toyotas, Nissans, Hondas, Suzukis, and Mitsubishi) plus European and American imports. It replicates core capabilities of Partsouq, RockAuto, and OEM EPCs by auto-populating Purchase Orders with VIN-decoded vehicle data, OEM part numbers, cross-reference interchange data, exploded view diagrams, and estimated landed costs. The architecture is **offline-first** (aggressive caching of all external API data and diagram images), **RHD-aware** (tracking steering position and market-specific fitment), and **cost-effective** (avoiding TecDoc subscriptions by combining free NHTSA vPIC, scraped OEM data, community EPC dumps, and manual curation).

---

## 2. Research Findings

### 2.1 GitHub Repository Audit — Top 10 Ranked

| Rank | Repository | Lang/Framework | License | Data Source | VIN? | Diagrams? | Interchange? | Pricing? | Score | Notes |
|------|-----------|----------------|---------|-------------|------|-----------|--------------|----------|-------|-------|
| 1 | [Wal33D/nhtsa-vin-decoder](https://github.com/Wal33D/nhtsa-vin-decoder) | Python/Java | MIT | NHTSA vPIC + offline WMI | ✅ | ❌ | ❌ | ❌ | 7/10 | Best offline VIN decoder for US-market vehicles. 2,015+ WMI codes. Zero deps. JDM coverage limited. |
| 2 | [cardog-ai/corgi](https://github.com/cardog-ai/corgi) | TypeScript/Node | ISC | NHTSA vPIC (SQLite) | ✅ | ❌ | ❌ | ❌ | 7/10 | ~20MB compressed offline DB. Fast <1ms decode. Good for browser/edge. |
| 3 | [davidpeckham/vpic-api](https://github.com/davidpeckham/vpic-api) | Python | MIT | NHTSA vPIC REST | ✅ | ❌ | ❌ | ❌ | 6/10 | Clean Python client. Typed objects. Good for Frappe server-side integration. |
| 4 | [ShaggyTech/nhtsa-api-wrapper](https://github.com/ShaggyTech/nhtsa-api-wrapper) | JavaScript/TS | MIT | NHTSA vPIC REST | ✅ | ❌ | ❌ | ❌ | 6/10 | Universal JS wrapper. Useful if we build a Frappe Page with Vue/React. |
| 5 | [ronhartman/tecdoc-autoparts-catalog](https://github.com/ronhartman/tecdoc-autoparts-catalog) / catamc90 | PHP/Symfony | ? | External API (TecDoc-like) | ❌ | ❌ | ✅ | ❌ | 5/10 | Decent TecDoc alternative wrapper. Requires API key. Good schema reference. |
| 6 | [ChanMeng666/Automotive-Repair-Management-System](https://github.com/ChanMeng666/Automotive-Repair-Management-System) | Python/Flask | MIT | Manual/MySQL | ❌ | ❌ | ❌ | ❌ | 5/10 | Good workshop job card schema inspiration. Not Frappe-native but useful reference. |
| 7 | [taimoorgit/vin-lookup-mcp](https://github.com/taimoorgit/vin-lookup-mcp) | Python | ? | NHTSA vPIC | ✅ | ❌ | ❌ | ❌ | 5/10 | MCP server wrapper. Niche use. |
| 8 | [tonycondone/modmaster-pro](https://github.com/tonycondone/modmaster-pro) | Python/Node/React | ? | AI + manual | ❌ | ❌ | ❌ | ❌ | 4/10 | AI image recognition for parts. Interesting future Phase 5 feature. |
| 9 | [lifeofcapo/car-api](https://github.com/lifeofcapo/car-api) (auto-parts-db) | JS/TS | ? | Manual/JSON | ❌ | ❌ | ❌ | ❌ | 4/10 | Lightweight 1200-part JS DB. Too basic for production. |
| 10 | [n8barr/automotive-model-year-data](https://github.com/n8barr/automotive-model-year-data) | CSV | ? | Community | ❌ | ❌ | ❌ | ❌ | 3/10 | Basic make/model/year CSV. Useful seed data only. |

**Key Insight:** No single open-source project delivers VIN + diagrams + interchange + pricing together. We must **compose** multiple sources behind a unified Frappe data layer.

### 2.2 Commercial Data Sources & Reverse Engineering Notes

#### A. NHTSA vPIC (Primary VIN Source)
- **URL:** `https://vpic.nhtsa.dot.gov/api/`
- **Cost:** FREE, no API key, no rate limit (fair use)
- **Endpoints:**
  - `GET /api/vehicles/decodevinvalues/{vin}?format=json`
  - `GET /api/vehicles/GetMakesForVehicleType/car?format=json`
- **Coverage:** US/Canada/Mexico homologated vehicles. Many JDM exports *do* appear because they were sold in US (e.g., Toyota Camry, Honda Accord). Grey-import JDM-only models (Toyota Vitz, Nissan AD Van) often **missing or incomplete**.
- **RHD Note:** vPIC returns `SteeringLocation` field — useful for validating RHD.
- **Verdict:** Use as primary decoder for 17-char VINs. Cache aggressively.

#### B. Partsouq.com
- **URL Patterns:**
  - VIN lookup: `https://partsouq.com/en/catalog/genuine/vehicle?c={make}&ssd={encoded}&vid=0&cid={cat}&cname={name}&q={vin}`
  - Diagram view: `https://partsouq.com/en/catalog/genuine/diagram?c={make}&ssd={encoded}&vid={vid}&gid={group}&did={diagram}`
- **API:** No public API. SSD parameter is a base64-like encoded state blob.
- **Scraping:** Possible but protected by Cloudflare. Data includes genuine OEM part numbers, prices in USD, diagram references, fitment data.
- **Ethics:** Respect `robots.txt`. Do not hammer. Cache heavily. Consider affiliate partnership instead of scraping.
- **Verdict:** Ethical scraping is high-risk. Better to use as **reference UI** and manually seed catalog from purchased parts histories.

#### C. Toyota EPC (toyota.epc-data.com) — FREE WEB EPC
- **URL:** `https://toyota.epc-data.com/` — search by frame number (e.g., `GXE10-0088644`)
- **Regions:** Japan, General, Europe, USA. For Dominica JDM imports, use **Japan** or **General** region.
- **Data:** Full genuine Toyota parts catalog with exploded diagrams, part numbers, applicability, and prices.
- **Access:** Completely free, no registration required. Web-based interface.
- **Connector Strategy:** Build a respectful scraper/connector that submits frame numbers, parses the resulting vehicle config page, then navigates parts groups to extract OEM numbers. Cache every page locally.
- **Verdict:** This is our **primary Toyota data source**. Zero cost, official data, no copyright grey area.

#### D. RockAuto.com
- **API:** None official.
- **Scraping:** Apify actor exists (`lexis-solutions/rockauto`). Returns brand, partNumber, price, fitmentNotes, warehouse.
- **Rate Limits:** Moderate anti-bot.
- **Verdict:** Useful for aftermarket interchange and pricing benchmarks. Use Apify or build respectful scraper with 1req/sec max.

#### E. TecDoc / TecAlliance
- **Cost:** €3,000–€10,000+/year commercial license.
- **Alt:** Gray-market SQL dumps circulate on Russian/Eastern European forums and r/DataHoarder.
- **Verdict:** Avoid official subscription for MVP. If gray-market dump obtained, use for cross-reference seeding only. Risk: license compliance.

#### F. Plenty.Parts / SixityAuto / Partsfits
- **Data:** Rich aftermarket interchange tables visible on product pages (OE ↔ aftermarket brand mappings).
- **API:** None found.
- **Verdict:** Reference only. Manual curation of high-volume interchange pairs.

### 2.3 Dominica Top 50 Vehicle Models (Best-Effort Fleet Profile)

Based on Japanese Car Trade import statistics, TCV popular rankings for Dominica (c=212), BE FORWARD testimonials, and regional Caribbean JDM patterns.

| # | Model | Make | Era | Body | Notes |
|---|-------|------|-----|------|-------|
| 1 | Hiace Van | Toyota | 1995–2020 | Van | Commercial workhorse. 2L/3L/5L/1KZ-TE/2KD-FTV |
| 2 | Hiace Regius / Super Custom | Toyota | 1997–2002 | Van | Passenger van variant |
| 3 | Hilux (Vigo, Revo) | Toyota | 2005–2020 | Pickup | 4x4 essential for terrain |
| 4 | Land Cruiser Prado | Toyota | 2003–2020 | SUV | Premium 4WD |
| 5 | RAV4 | Toyota | 2001–2020 | SUV | Popular family car |
| 6 | Corolla Axio / Fielder | Toyota | 2007–2020 | Sedan/Wagon | 1NZ-FE, 2NZ-FE |
| 7 | Vitz / Yaris | Toyota | 2005–2020 | Hatch | 1KR-FE, 1NZ-FE |
| 8 | Passo | Toyota | 2005–2020 | Hatch | Budget city car |
| 9 | Probox / Succeed | Toyota | 2002–2020 | Van | Delivery/commercial |
| 10 | Noah / Voxy | Toyota | 2007–2020 | Minivan | Large family |
| 11 | Wish | Toyota | 2003–2017 | MPV | Family mover |
| 12 | Premio / Allion | Toyota | 2007–2020 | Sedan | 1NZ, 2ZR |
| 13 | Mark X | Toyota | 2004–2019 | Sedan | 4GR/2GR V6 |
| 14 | Vanguard | Toyota | 2008–2013 | SUV | 7-seat RAV4 cousin |
| 15 | Harrier | Toyota | 2003–2020 | SUV | Lexus RX cousin |
| 16 | AD Van / AD Expert | Nissan | 2007–2020 | Van | QG15DE, HR15DE |
| 17 | NV150 AD | Nissan | 2013–2020 | Van | Commercial van |
| 18 | Note | Nissan | 2005–2020 | Hatch | HR15DE, HR12DE |
| 19 | Tiida Latio | Nissan | 2004–2012 | Sedan | HR15DE |
| 20 | X-Trail | Nissan | 2003–2020 | SUV | T30/T31/T32 |
| 21 | Serena | Nissan | 2005–2020 | Minivan | QR20/25, MR20 |
| 22 | Caravan / Urvan | Nissan | 2001–2020 | Van | Commercial |
| 23 | Wingroad | Nissan | 2005–2018 | Wagon | QG/HR engines |
| 24 | Bluebird Sylphy | Nissan | 2006–2012 | Sedan | QR20/HR15 |
| 25 | March / Micra | Nissan | 2003–2010 | Hatch | City runabout |
| 26 | Navara | Nissan | 2005–2020 | Pickup | YD25/QR25 |
| 27 | Fit / Jazz | Honda | 2005–2020 | Hatch | L13A, L15A |
| 28 | Fit Shuttle | Honda | 2011–2016 | Wagon | Fit estate |
| 29 | CR-V | Honda | 2005–2020 | SUV | K20A, R20A |
| 30 | HR-V / Vezel | Honda | 2014–2020 | SUV | Crossover popular |
| 31 | Stream | Honda | 2006–2014 | MPV | R18A, R20A |
| 32 | Stepwgn | Honda | 2005–2020 | Minivan | K20A, R20A |
| 33 | Civic | Honda | 2006–2020 | Sedan/Hatch | R18A, L15B |
| 34 | Accord | Honda | 2003–2020 | Sedan | K24A |
| 35 | Swift | Suzuki | 2005–2020 | Hatch | M13A, K12B, K14C |
| 36 | Alto | Suzuki | 2005–2020 | Hatch | Budget kei-class feel |
| 37 | Every / Carry | Suzuki | 2005–2020 | Van/Truck | Commercial micro |
| 38 | Escudo / Vitara | Suzuki | 2005–2020 | SUV | J20A, M16A |
| 39 | Jimny | Suzuki | 2012–2020 | SUV | Off-road favorite |
| 40 | Lancer / Cedia | Mitsubishi | 2003–2010 | Sedan | 4G15, 4G93 |
| 41 | Pajero / Montero | Mitsubishi | 2003–2020 | SUV | 4M41, 6G72 |
| 42 | L200 / Triton | Mitsubishi | 2005–2020 | Pickup | 4D56, 4N15 |
| 43 | Delica | Mitsubishi | 2005–2020 | Van | 4WD van |
| 44 | Outlander | Mitsubishi | 2005–2020 | SUV | 4B11, 4B12 |
| 45 | Golf | Volkswagen | 2005–2020 | Hatch | European diesel/petrol |
| 46 | Polo | Volkswagen | 2005–2020 | Hatch | Budget European |
| 47 | Passat | Volkswagen | 2005–2020 | Sedan/Wagon | B6/B7 |
| 48 | Tiguan | Volkswagen | 2009–2020 | SUV | Compact SUV |
| 49 | Transit / Tourneo | Ford | 2005–2020 | Van | Commercial Euro import |
| 50 | Ranger | Ford | 2012–2020 | Pickup | PX/PX2 | 

**RHD Implications:** Dominica drives on the LEFT. All imports are RHD. Critical parts differences from LHD:
- **Headlights:** Beam pattern angled left (RHD units differ from LHD)
- **Wipers:** Arm orientation often reversed
- **Steering rack / column:** RHD-specific
- **Dashboard / HVAC:** RHD layout
- **Side mirrors:** Convexity and mounting differ
- **Master cylinder / booster:** Sometimes positioned for RHD firewall

The system MUST track `steering_position` (RHD/LHD) and `market_code` (JDM/UKDM/AUDM) on every Vehicle and Part Catalog applicability record.

---

## 3. Frappe App Architecture

### 3.1 App Structure

```
partscape/
├── partscape/
│   ├── __init__.py
│   ├── hooks.py
│   ├── patches.txt
│   ├── api/
│   │   ├── __init__.py
│   │   ├── vin_decoder.py
│   │   ├── partsouq_scraper.py
│   │   ├── toyota_epc_connector.py
│   │   ├── interchange_api.py
│   │   ├── landed_cost_api.py
│   │   └── data_pipeline.py
│   ├── doctype/
│   │   ├── vehicle/
│   │   ├── vehicle_make/
│   │   ├── vehicle_model/
│   │   ├── vehicle_engine_variant/
│   │   ├── part_catalog/
│   │   ├── part_category/
│   │   ├── part_interchange/
│   │   ├── vin_decode_cache/
│   │   ├── workshop_job_card/
│   │   ├── workshop_job_card_part/
│   │   ├── workshop_job_card_po/
│   │   ├── workshop_job_card_stock_entry/
│   │   ├── customer_vehicle/
│   │   ├── vehicle_part_applicability/
│   │   └── part_supplier_reference/
│   ├── utils/
│   │   ├── __init__.py
│   │   ├── item_factory.py
│   │   ├── po_hooks.py
│   │   ├── stock_hooks.py
│   │   └── customer_hooks.py
│   ├── data_import/
│   │   ├── import_part_catalog.py
│   │   ├── import_vehicle_master.py
│   │   └── csv_templates/
│   ├── public/
│   │   └── js/
│   │       ├── purchase_order.js
│   │       ├── item.js
│   │       ├── stock_entry.js
│   │       └── workshop_job_card.js
│   ├── fixtures/
│   │   ├── custom_field.json
│   │   ├── property_setter.json
│   │   └── role.json
│   └── config/
│       └── desktop.py
├── requirements.txt
└── setup.py
```

### 3.2 DocType Schema (ER Diagram Summary)

```text
VehicleMake (1) ───< (N) VehicleModel (1) ───< (N) VehicleEngineVariant (1) ───< (N) VehiclePartApplicability (N) >─── (1) PartCatalog

Vehicle (1) ───> (1) VehicleModel
Vehicle (1) ───> (1) VehicleEngineVariant (optional)
Vehicle (N) >─── (1) Customer
Customer (1) ───< (N) CustomerVehicle (N) >─── (1) Vehicle

PartCatalog (1) ───< (N) PartInterchange (N) >─── (1) PartCatalog (bidirectional graph edge)
PartCatalog (1) ───< (N) PartSupplierReference (N) >─── (1) Supplier
PartCatalog (1) ───< (N) VehiclePartApplicability
PartCatalog (1) ───< (N) PartCatalogDiagram (N) >─── (1) PartDiagram

VehicleModel (1) ───< (N) PartDiagram

WorkshopJobCard (1) ───< (N) WorkshopJobCardPart
WorkshopJobCardPart (N) >─── (1) PartCatalog
WorkshopJobCard (1) ───> (1) Vehicle

VINDecodeCache (standalone lookup)
```

### 3.3 Core DocType Specifications

#### Vehicle Make
| Field | Type | Notes |
|-------|------|-------|
| make_name | Data | e.g., "Toyota" |
| wmi_codes | Data | Comma-separated WMI prefixes |
| country_of_origin | Data | Japan, Germany, USA |
| is_jdm_primary | Check | Flag for JDM-heavy makes |

#### Vehicle Model
| Field | Type | Notes |
|-------|------|-------|
| model_name | Data | e.g., "Hiace" |
| make | Link | Vehicle Make |
| model_code | Data | e.g., "KDH201" |
| body_type | Select | Sedan, Hatch, SUV, Van, Pickup, MPV, Wagon |
| year_start | Int | |
| year_end | Int | |
| steering_position | Select | RHD, LHD, Both |
| primary_market | Select | JDM, UKDM, AUM, USDM, EUDM |

#### Vehicle Engine Variant
| Field | Type | Notes |
|-------|------|-------|
| variant_name | Data | e.g., "2.8 Diesel Turbo" |
| model | Link | Vehicle Model |
| engine_code | Data | e.g., "1KZ-TE", "QG15DE" |
| displacement | Data | e.g., "2982 cc" |
| fuel_type | Select | Petrol, Diesel, Hybrid, Electric |
| transmission | Select | 5MT, 6MT, 4AT, CVT, etc. |
| drivetrain | Select | 2WD, 4WD, AWD |
| power_kw | Float | |
| torque_nm | Float | |

#### Vehicle (Unit Master)
| Field | Type | Notes |
|-------|------|-------|
| vin | Data | Unique. 17-char VIN or JDM chassis/frame no |
| chassis_number | Data | JDM frame number if different from VIN |
| make | Link | Vehicle Make |
| model | Link | Vehicle Model |
| variant | Link | Vehicle Engine Variant |
| year | Int | Model year |
| engine_code | Data | Denormalized from variant |
| transmission | Data | Denormalized |
| color | Data | |
| registration_no | Data | Dominica plate |
| owner | Link | Customer |
| country_of_origin | Data | Japan, UK, etc. |
| import_date | Date | |
| mileage | Int | KM |
| steering_position | Select | RHD, LHD |
| market_code | Data | JDM, UKDM, etc. |
| status | Select | Active, Workshop, Scrapped, Sold |
| last_vin_decode | Datetime | |
| decoded_json | Code | Full NHTSA/vPIC response |

#### Part Catalog (Universal Parts Registry)
| Field | Type | Notes |
|-------|------|-------|
| brand | Data | Required. e.g., "Toyota", "Bosch", "Denso" |
| part_number | Data | Required. e.g., "04465-26421" |
| part_name | Data | e.g., "Brake Pad Set, Disc" |
| vehicle_make | Link | Vehicle Make this part is FOR |
| is_oem | Check | Auto-set when brand == vehicle_make |
| category | Link | Part Category |
| description | Text | |
| diagram_reference | Data | e.g., "B-15" in exploded view |
| weight_kg | Float | |
| dimensions | Data | LxWxH mm |
| images | Attach Image | Multiple via File doctype |
| diagrams | Table | Part Catalog Diagram (child table) — links to exploded view diagrams |
| superseded_by | Link | Part Catalog (self) |
| is_active | Check | |
| estimated_cost_usd | Currency | Base cost before landed calc |
| steering_position | Select | RHD, LHD, Universal |
| market_restriction | Data | JDM-only, etc. |

**Identity:** The composite `(brand, part_number)` is the unique key. "Toyota 04465-26421" and "Bosch 0 986 494 046" are two distinct rows. OEM parts are simply rows where `brand == vehicle_make`.

#### Part Interchange (Bidirectional Graph Edge)
| Field | Type | Notes |
|-------|------|-------|
| part_a | Link | Part Catalog (required) |
| part_b | Link | Part Catalog (required) |
| relationship_type | Select | Equivalent, Superseded By, Aftermarket Alternative |
| quality_tier | Select | OEM, OEM Equivalent, Aftermarket, Performance |
| confidence_score | Float | 0.0 – 1.0 |
| source | Data | Where cross-reference confirmed |

**Model:** Interchange is a graph, not a list. `Toyota 04465-26421` ↔ `Bosch 0 986 494 046` is one undirected edge. Querying from either direction works. Aftermarket brands inherit vehicle applicability by walking the interchange graph from the OEM node.

#### Part Diagram (Exploded View Image)
| Field | Type | Notes |
|-------|------|-------|
| vehicle_model | Link | Vehicle Model this diagram belongs to |
| parts_group | Data | e.g. "Brake System", "Engine" |
| diagram_page | Data | e.g. "B-15", "Group 22" |
| diagram_number | Data | SHA-256 hash (deduplication key) |
| diagram_image | Attach Image | The actual exploded view image file |
| source_url | Data | Original web URL where scraped |
| source_brand | Data | e.g. "Toyota", "7zap", "RealOEM" |
| is_active | Check | |

**Storage:** Diagram images are stored as private Frappe file attachments. A single diagram (e.g., front brake assembly for Hiace KDH201) is stored once and linked to all 20-50 parts visible on that diagram via the `Part Catalog Diagram` child table.

#### Part Catalog Diagram (Child Table)
| Field | Type | Notes |
|-------|------|-------|
| part_diagram | Link | Part Diagram |
| callout_number | Data | The number on the diagram pointing to this part |
| parts_group | Data | Denormalized for quick reference |

#### Vehicle Part Applicability (Child Table / Separate DocType)
| Field | Type | Notes |
|-------|------|-------|
| part_catalog | Link | Part Catalog |
| vehicle_model | Link | Vehicle Model |
| variant | Link | Vehicle Engine Variant (optional) |
| year_start | Int | |
| year_end | Int | |
| steering_position | Select | RHD, LHD, Universal |
| market_code | Data | |
| part_diagram | Link | Part Diagram (optional) — links to exploded view |
| diagram_page | Data | Text reference to diagram page |

#### Part Supplier Reference (Child Table / Separate DocType)
| Field | Type | Notes |
|-------|------|-------|
| part_catalog | Link | Part Catalog |
| supplier | Link | Supplier |
| supplier_part_number | Data | |
| moq | Int | Minimum order qty |
| lead_time_days | Int | |
| unit_cost_usd | Currency | |
| currency | Link | Currency |

#### VIN Decode Cache
| Field | Type | Notes |
|-------|------|-------|
| vin | Data | Unique |
| decoded_json | JSON | Full API response |
| make | Data | Extracted |
| model | Data | Extracted |
| year | Int | Extracted |
| engine_code | Data | Extracted |
| steering_location | Data | vPIC field |
| source_api | Data | NHTSA, JAPIC, Manual |
| last_decoded | Datetime | |
| hit_count | Int | How many times used |

#### Workshop Job Card
| Field | Type | Notes |
|-------|------|-------|
| vehicle | Link | Vehicle |
| complaint | Text | Customer complaint |
| diagnosis | Text | |
| status | Select | Open, Parts Required, In Progress, Completed, Invoiced |
| parts_required | Table | Workshop Job Card Part |
| linked_purchase_orders | Table | Link to POs |
| linked_stock_entries | Table | Link to consumption |
| labor_hours | Float | |
| technician | Link | Employee |

#### Workshop Job Card Part (Child Table)
| Field | Type | Notes |
|-------|------|-------|
| part_catalog | Link | Part Catalog |
| qty | Float | |
| source | Select | Stock, Order, Customer Supplied, Cannibalize |
| item | Link | Item (if mapped to stock) |
| actual_cost | Currency | At time of job |
| supplied_via | Link | Stock Entry or Purchase Order |

#### Customer Vehicle (Child Table on Customer)
| Field | Type | Notes |
|-------|------|-------|
| vehicle | Link | Vehicle |
| vin | Data | Fetched from Vehicle.vin (read-only) |
| make_model | Data | Fetched from Vehicle.model (read-only) |
| year | Int | Fetched from Vehicle.year (read-only) |
| is_primary | Check | Only one vehicle per customer can be primary |
| date_added | Date | |

**Sync Logic:** When a Vehicle's `owner` is set to a Customer, the system auto-adds it to that Customer's `vehicles` child table. When a vehicle is removed from the Customer's table, its `owner` field is cleared. This ensures bidirectional integrity.

### 3.4 Custom Fields on Existing ERPNext DocTypes

#### Item
- `brand` (Data) — indexed
- `part_number` (Data) — indexed
- `part_catalog_reference` (Link → Part Catalog)
- `quality_tier` (Select)
- `vehicle_fitment_summary` (Text) — auto-generated

#### Purchase Order Item
- `vehicle` (Link → Vehicle)
- `vin` (Data) — copied from Vehicle
- `part_catalog_reference` (Link → Part Catalog)
- `alternative_part_numbers` (Text) — comma-separated interchange list
- `diagram_reference` (Data)
- `estimated_landed_cost_xcd` (Currency) — computed
- `applicable_models` (Text) — auto-populated

#### Stock Entry Detail
- `vehicle_consumed_by` (Link → Vehicle)
- `job_card_reference` (Link → Workshop Job Card)
- `part_catalog_reference` (Link → Part Catalog)

#### Supplier
- `part_brands_supplied` (Table) — brand + category
- `preferred_shipping_method` (Data)
- `average_lead_time_days` (Int)

#### Customer
- `vehicles` (Table → Customer Vehicle) — all vehicles owned by this customer
- `primary_vehicle` (Link → Vehicle) — auto-set from the row marked `is_primary`

### 3.5 Permission Model

| Role | Vehicle | Part Catalog | Part Interchange | Workshop Job Card | PO/Item/Stock |
|------|---------|--------------|------------------|-------------------|---------------|
| Fleet Manager | R/W | R/W (seed) | R/W (seed) | R/W | R/W |
| Parts Clerk | R | R | R | R/W | R/W |
| Mechanic | R | R | R | R/W (own jobs) | R (consumption only) |
| Purchase Officer | R | R | R | R | R/W |
| Accountant | R | R | R | R | R/W |
| System Manager | All | All | All | All | All |

**Note:** Part Catalog should be marked as `read_only` for non-Manager roles via Permission Level 1 to prevent accidental corruption of reference data.

---

## 4. API & Data Pipeline Architecture

### 4.1 VIN Decoder Service

**Strategy:** Cache-first with fallback chain.

```python
# Pseudo-flow
def decode_vin(vin: str) -> dict:
    cache = frappe.get_doc("VIN Decode Cache", {"vin": vin})
    if cache and cache.last_decoded > add_days(now(), -90):
        return cache.decoded_json
    
    # 1. Try NHTSA vPIC (free, 17-char VINs)
    result = nhtsa_decode(vin)
    
    # 2. If JDM chassis number or NHTSA empty:
    if not result:
        result = japic_or_manual_lookup(vin)
    
    # 3. Persist cache
    create_or_update_vin_cache(vin, result)
    return result
```

**NHTSA Integration:** Use `requests` to call `https://vpic.nhtsa.dot.gov/api/vehicles/decodevinvalues/{vin}?format=json`. Parse `Results[0]` for make, model, year, engine, `SteeringLocation`.

**JDM Chassis Numbers:** Japanese vehicles often use Frame Numbers (e.g., `KDH201-0149586`). These are NOT 17-char VINs. NHTSA will fail. Solution:
- Parse frame number prefix (`KDH201`) against `VehicleModel.model_code` lookup table.
- Extract known engine codes from prefix (e.g., `K` = 2KD-FTV in Toyota codes).
- Manual mapping table for Dominica's top 50 models is essential.

### 4.2 Parts Diagram & OEM Data Ingestion

**The epc-data.com Network (All Brands, Day One):**
The `epc-data.com` domain operates a **free web EPC network** across multiple brands:
- `toyota.epc-data.com`
- `nissan.epc-data.com`
- `honda.epc-data.com`
- `suzuki.epc-data.com`
- `mitsubishi.epc-data.com`
- `mazda.epc-data.com`
- `subaru.epc-data.com`

Every site accepts frame numbers or VINs and returns genuine OEM parts data. Zero cost. No registration.

**Strategy:**
1. Build a generic EPC connector class parameterized by brand and base URL.
2. Seed ALL brands in parallel from day one — not Toyota-first.
3. Toyota gets priority for *depth* (more parts per model), but Nissan, Honda, Suzuki, and Mitsubishi get seeded in *parallel* for *breadth*.
4. Every page and part number fetched is persisted in `Part Catalog` (brand + part_number) and `Vehicle Part Applicability`.
5. **Diagram images are downloaded and cached.** Every exploded view diagram encountered during scraping is saved as a `Part Diagram` record with the actual image file attached. Parts are linked to their diagrams via the `Part Catalog Diagram` child table with callout numbers.
6. After the initial seed, the system is offline-first: all external data, part numbers, fitment data, and diagram images are cached locally.

**Multibrand Free Aggregators (European / American / All Brands):**
Several free web portals provide OEM parts data across dozens of brands without registration:

| Source | Brands Covered | Access | Notes |
|--------|---------------|--------|-------|
| `7zap.com` | 60+ brands including Ford, VW, BMW, Mercedes, Audi, Opel, Renault, Volvo | Free web, VIN search | Exploded diagrams, OEM numbers, cross-references. Primary fallback for non-Japanese brands. |
| `realoem.com` | BMW (primary), Audi, Mercedes, Porsche, Saab, VW | Free web, VIN/model search | Very clean interface. BMW coverage is exceptional. |
| `ilcats.ru` | All major makes | Free web | Russian-registered but English-navigable. Deep catalog coverage. |
| `nemigaparts.com` | BMW, Mercedes, Porsche, Audi, Mini, Smart | Free web | Clean ETK/EPC clones for German brands. |
| `ford.7zap.com` | Ford (Europe-focused) | Free web, VIN search | Dedicated Ford portal within 7zap network. |
| `webautocats.com` | BMW ETK, VW ETKA, Mercedes EPC, Porsche PET, Opel EPC | Free web | Niche but deep German-brand coverage. |

**Tiered Strategy by Brand:**

| Tier | Brands | Primary Source | Secondary Source |
|------|--------|---------------|------------------|
| 1 (JDM) | Toyota, Nissan, Honda, Suzuki, Mitsubishi, Mazda, Subaru | `{brand}.epc-data.com` | `partsouq.com`, `amayama.com`, `megazip.net` |
| 2 (Euro) | VW, BMW, Mercedes, Audi, Opel, Renault, Volvo, Peugeot | `7zap.com`, `realoem.com`, `nemigaparts.com` | `ilcats.ru`, `webautocats.com` |
| 3 (American) | Ford, GM (Chevy/Cadillac/GMC), Chrysler/Jeep | `ford.7zap.com`, `7zap.com` | `ilcats.ru`, aftermarket interchange sheets |
| 4 (Universal) | Bosch, Denso, KYB, NGK, Aisin, TRW, Akebono | Brand cross-reference Excel/PDF sheets | RockAuto, Plenty.Parts |

**American Brand Nuances:**
- **Ford:** `ford.7zap.com` provides genuine Ford parts with VIN search. Ford Transit and Ranger are the most common Ford imports in Dominica.
- **GM (Chevrolet, GMC, Cadillac, Buick):** No free official web EPC found. `7zap.com` has limited GM coverage. Best approach: seed top 200 fast-moving parts from `partsouq.com` / `megazip.net` + manual curation from purchase history.
- **Chrysler / Jeep / Dodge (MOPAR):** `7zap.com` has limited coverage. Aftermarket interchange sheets are the primary source for common parts (brake pads, filters, belts).

**European Brand Nuances:**
- **BMW:** `realoem.com` is exceptional and free. VIN-based lookup with full ETK diagram navigation.
- **VW/Audi/Skoda/Seat:** `7zap.com` and `webautocats.com` (ETKA clone) provide genuine parts data.
- **Mercedes/Smart:** `nemigaparts.com/mercedes` and `7zap.com` provide EPC data.
- **Opel/Vauxhall:** `webautocats.com` and `7zap.com` cover European-market models.
- **Volvo:** `7zap.com` has Volvo coverage; `volvopartswebshop.com` as backup reference.

**Key Principle:** The `Part Catalog` universal registry (brand + part_number) does not care where a part came from. Whether it's Toyota from `toyota.epc-data.com`, BMW from `realoem.com`, or Ford from `ford.7zap.com`, every row obeys the same schema. The interchange graph connects them all.

### 4.3 Aftermarket Interchange Pipeline

**Sources:**
1. **RockAuto scraper** (Apify or custom): Extract `Part Interchange` lists from product pages.
2. **Plenty.Parts**: Manual curation of high-volume parts (brake pads, oil filters, spark plugs).
3. **Brand catalogs**: Many aftermarket brands (Bosch, Denso, Aisin, KYB, NGK) publish Excel cross-reference sheets. Download and import.

**Confidence Scoring:**
- `1.0` = Confirmed by manufacturer catalog (Bosch says `0 986 494 046` = Toyota `04465-26421`).
- `0.8` = Confirmed by two independent sources.
- `0.5` = Scraped from single marketplace.
- `0.2` = Fuzzy string match (use with caution).

### 4.4 Scheduled Job: Nightly Sync

Defined in `hooks.py` under `scheduler_events.daily`:

```python
# partscape/hooks.py
scheduler_events = {
    "daily": [
        "partscape.api.data_pipeline.run_daily_sync"
    ]
}
```

**Pipeline Steps:**
1. Find `Vehicle` docs created in last 24h with empty decoded VIN → run VIN decode.
2. For decoded vehicles, query known APIs for model-specific parts lists → create missing `Part Catalog` entries.
3. Run fuzzy match between existing `Item` codes and `Part Catalog` (brand + part_number) → auto-link.
4. Pull interchange updates from configured aftermarket sources.
5. Recompute `estimated_landed_cost_xcd` for all `Purchase Order` drafts based on latest supplier refs + customs formula.

---

## 5. Implementation Roadmap

### Phase 1: Foundation — VIN + Universal Registry (Weeks 1–2)
- [x] Create Frappe app scaffold + DocTypes: Vehicle Make, Model, Engine Variant, Vehicle, VIN Decode Cache.
- [x] Implement `vin_decoder.py` (NHTSA API + cache).
- [x] Create `Part Catalog` (brand + part_number universal registry) + `Part Category` DocTypes.
- [x] Create `Part Interchange` (bidirectional graph edge) DocType.
- [x] Add custom fields to `Item` and `Purchase Order Item`.
- [x] Client script: PO Item auto-fill from Part Catalog selection.
- [x] Landed cost calculator (USD → XCD with customs %).
- [ ] Implement JDM frame number parser for all Japanese makes.
- [ ] Build generic EPC connector class parameterized by brand + base URL.

### Phase 2: Parallel Brand Seeding — All JDM + Euro + American (Weeks 3–4)
- [ ] Seed Toyota (depth) via `toyota.epc-data.com` — all parts for Hiace/Hilux/Vitz/Corolla.
- [ ] Seed Nissan (breadth) via `nissan.epc-data.com` — top 200 parts for AD Van/Note/X-Trail.
- [ ] Seed Honda (breadth) via `honda.epc-data.com` — top 200 parts for Fit/CR-V/Stream.
- [ ] Seed Suzuki, Mitsubishi, Mazda, Subaru (breadth) via respective `.epc-data.com` sites.
- [ ] Seed Ford (breadth) via `ford.7zap.com` — Transit/Ranger top 100 parts.
- [ ] Seed VW, BMW, Mercedes (breadth) via `7zap.com` / `realoem.com` / `nemigaparts.com`.
- [ ] Import Bosch/Denso/KYB/NGK cross-reference sheets into `Part Interchange` graph.
- [ ] Build `Vehicle Part Applicability` importer from CSV.

### Phase 3: Interchange + Aftermarket + Pricing (Weeks 5–6)
- [ ] Build RockAuto scraper (respectful, cached) for pricing benchmarks.
- [ ] Implement fuzzy matching engine (`difflib`/`rapidfuzz`) to link existing warehouse Items to Part Catalog.
- [ ] Diagram image storage + viewer in Part Catalog form.
- [ ] Build `Part Supplier Reference` table with MOQ/lead time.

### Phase 4: Workshop Job Card + Consumption Tracking (Weeks 7–8)
- [ ] Build `Workshop Job Card` DocType with parts table.
- [ ] Link Job Card → Stock Entry (consumption) and Purchase Order (ordering).
- [ ] Track vehicle-specific part consumption for warranty.
- [ ] Reports: Vehicle service history, parts consumption by model.
- [ ] Dashboard: Top failing parts, vehicle downtime, stock levels vs. demand.

### Phase 5: Mobile PWA for Mechanics (Weeks 9–12)
- [ ] Frappe Mobile / custom PWA.
- [ ] Barcode/QR scan of VIN/frame number → auto-decode.
- [ ] Photo capture of failed part → manual part catalog search.
- [ ] Offline queue: create job cards and PO requests without internet; sync when connected.

---

## 6. Code Samples

### 6.1 Frappe Controller: Create Item from Part Catalog

See file: `partscape/partscape/utils/item_factory.py`

### 6.2 VIN Decode Cache Wrapper

See file: `partscape/partscape/api/vin_decoder.py`

### 6.3 Purchase Order Client Script

See file: `partscape/partscape/public/js/purchase_order.js`

### 6.4 Partsouq Scraper Stub

See file: `partscape/partscape/api/partsouq_scraper.py`

### 6.5 Data Import Script

See file: `partscape/partscape/data_import/import_part_catalog.py`

---

## 7. Risk & Compliance

### 7.1 Copyright / Database Rights
- **OEM Part Numbers:** Generally considered factual data. In most jurisdictions (including US and Commonwealth Caribbean), raw part numbers, dimensions, and fitment data are **not copyrightable** (Feist v. Rural).
- **Diagram Images:** Exploded view diagrams from Toyota/Nissan/BMW EPCs ARE copyrighted by their respective manufacturers. Our approach: download and cache them as **private file attachments** within Frappe for internal business use only (repair shop operations). They are never exposed publicly, redistributed, or included in customer-facing SaaS. This falls under fair use/dealing for internal repair reference.
- **TecDoc:** Commercial database. Do not use gray-market dumps in customer-facing SaaS. Internal use within a single company's ERP is lower risk, but not zero.
- **Mitigation:** Build our own `Part Catalog` from free web EPCs (factual data), public manufacturer cross-references, and manual curation. This creates a clean-room dataset. Diagram images are cached locally but treated as confidential internal assets.

### 7.2 Scraping Ethics
- Always respect `robots.txt`.
- Rate limit to ≤1 req/sec.
- Cache aggressively; never scrape same page twice in 30 days.
- Use affiliate APIs where available (Partsouq, RockAuto) instead of scraping.
- **Partsouq specifically:** They are a small business serving the JDM community. Consider reaching out to `info@partsouq.com` for a data partnership or affiliate arrangement before scraping.

### 7.3 GDPR / Privacy
- VINs are considered **Personal Data** under GDPR if linked to an identifiable owner.
- Dominica is not GDPR-regulated, but best practice applies.
- **Mitigation:** Store VIN in `Vehicle` doc. Restrict read access via role permissions. Do not transmit VINs to third-party APIs unless necessary. Use `VIN Decode Cache` to minimize external sharing.

### 7.4 Dominican Customs / Landed Cost
- Dominica customs duties on auto parts vary by HS code.
- Typical calculation: CIF Value × Import Duty (varies) + VAT (15%) + Customs Service Charge + Environmental Levy (if applicable).
- **Mitigation:** Build configurable landed cost formula in `Landed Cost Voucher` hook. Allow customs rate tables per HS code. Default to 25% duty + 15% VAT for automotive parts as conservative estimate.

---

## 8. Data Source Comparison Matrix

| Source | Cost | Coverage | JDM Fit | RHD Aware | API? | License Risk | Recommended Use |
|--------|------|----------|---------|-----------|------|--------------|-----------------|
| NHTSA vPIC | Free | US/CA vehicles | Partial | Yes (field) | REST | None | Primary VIN decode for 17-char |
| CarQuery | Freemium | Global specs | Partial | No | REST | Low | Vehicle specs fallback |
| Toyota EPC Web | Free | Toyota/Lexus global | Yes | Yes | Web/Scrape | Low | OEM numbers + diagram images |
| Nissan EPC Web | Free | Nissan/Infiniti global | Yes | Yes | Web/Scrape | Low | OEM numbers + diagram images |
| Honda EPC Web | Free | Honda/Acura global | Yes | Yes | Web/Scrape | Low | OEM numbers + diagram images |
| 7zap.com | Free | 60+ brands | Yes | Yes | Web/Scrape | Low | OEM numbers + diagram images |
| RealOEM.com | Free | BMW + German brands | Partial | No | Web/Scrape | Low | OEM numbers + diagram images |
| Partsouq | Per-use | Toyota/Nissan/Honda/etc | Yes | Yes | None | Med (scraping) | Reference UI / manual seed |
| RockAuto | Per-use | Aftermarket global | Partial | No | None | Med (scraping) | Pricing + interchange |
| TecDoc | €€€€ | Aftermarket global | Yes | Yes | SOAP/REST | High (gray dumps) | Avoid officially |
| Manufacturer X-Ref Sheets | Free | Brand-specific | Yes | Sometimes | Excel/PDF | None | Interchange seeding |
| JAPIC (Japan) | Unknown | JDM chassis | Yes | Yes | Unknown | Unknown | Research pending |

---

## 9. Next Steps / Action Items

1. **Approve architecture** — Review this blueprint with Seityl stakeholders.
2. **Procure data seeds** — Use `toyota.epc-data.com` (free) for Toyota parts. Download Bosch/Denso/Aisin cross-reference Excel sheets. Download exploded view diagrams from all accessible EPC sources.
3. **Setup dev bench** — `bench new-app partscape` on local Frappe v15 dev environment.
4. **Import Dominica Top 50** — Create Vehicle Make/Model/Variant records for the top 50 models listed in §2.3.
5. **Build VIN decoder** — Implement NHTSA wrapper + cache. Test with 20 real Dominica VINs.
6. **Custom fields + scripts** — Apply fixtures for Item, PO, Stock Entry, **Customer** customizations.
7. **Customer-Vehicle linking** — Add `vehicles` child table to Customer. Test bidirectional sync with Vehicle.owner.
8. **Pilot with Toyota** — Use `toyota.epc-data.com` to seed brake pads, oil filters, belts for Hiace KDH20x. Create 3 test POs.
9. **Partner outreach** — Email Partsouq and Amayama about affiliate/data API access.
10. **Legal review** — Confirm Dominica customs duty rates and database copyright position with local counsel.
11. **Schedule Phase 1 sprint** — 2-week agile sprint with daily standups. Target: working PO auto-populate for Toyota parts.

---

*Document prepared by AI Architect for Seityl Group Ltd. All schemas and code samples are illustrative and subject to refinement during implementation.*
