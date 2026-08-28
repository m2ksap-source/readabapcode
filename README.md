# readabapcode

Read ABAP source code from an SAP BTP ABAP Environment trial with a headless
Python script. It calls the same ADT (ABAP Development Tools) REST API that
Eclipse uses and authenticates via the OAuth 2.0 password grant, so no browser
or SSO prompt is involved.

The tool is read-only: it only issues `GET` requests and cannot lock or modify
anything in the system.

## Contents

```
readabapcode/
├── abap_session.py     # OAuth token handling + one authenticated GET
├── check_connection.py # connectivity/authentication check
├── read_abap.py        # CLI: read a class / interface / include / function module
├── .env.example        # connection template
└── requirements.txt
```

## Requirements

- An SAP BTP ABAP Environment trial ("ABAP Cloud Developer Trial"). The
  configured user needs developer authorization - the same user used for ADT
  in Eclipse.
- Python 3.9 or later.
- `requests` and `python-dotenv`.

## Authentication

ADT in Eclipse logs in through a browser via SAML, which a script cannot do.
This tool uses the OAuth 2.0 password grant against the XSUAA instance in front
of the ABAP system:

1. `POST {OAUTH_URL}/oauth/token` with
   - `grant_type=password`
   - `username` / `password` - the BTP/ABAP developer login
   - HTTP basic auth - the `clientid` / `clientsecret` from a service key
2. XSUAA returns a bearer token carrying the user's ABAP identity and
   authorizations.
3. Each ADT call sends `Authorization: Bearer <token>`.

Because the token represents a named user, no Communication Arrangement is
required; the user's existing developer authorizations apply.

## Setup

### 1. Create a service key

BTP cockpit → subaccount → Instances and Subscriptions → the ABAP environment
instance → Service Keys → Create.

Four values are needed from the key:

| Service key field   | Variable        |
|---------------------|-----------------|
| `url` (root)        | `ABAP_HOST`     |
| `uaa.url`           | `OAUTH_URL`     |
| `uaa.clientid`      | `CLIENT_ID`     |
| `uaa.clientsecret`  | `CLIENT_SECRET` |

Relevant part of a service key:

```json
{
  "url": "https://<subdomain>.abap.us10.hana.ondemand.com",
  "uaa": {
    "clientid": "sb-...",
    "clientsecret": "...",
    "url": "https://<subdomain>.authentication.us10.hana.ondemand.com"
  }
}
```

### 2. Install

```powershell
cd readabapcode
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### 3. Configure

Copy `.env.example` to `.env` and fill in the values:

```ini
ABAP_HOST=https://your-subdomain.abap.us10.hana.ondemand.com
OAUTH_URL=https://your-subdomain.authentication.us10.hana.ondemand.com
CLIENT_ID=your_client_id
CLIENT_SECRET=your_client_secret
SAP_CLIENT=100

ABAP_USERNAME=your_btp_username
ABAP_PASSWORD=your_btp_password
```

`ABAP_HOST`, `OAUTH_URL`, `CLIENT_ID`, `CLIENT_SECRET`, `ABAP_USERNAME` and
`ABAP_PASSWORD` are all required; a missing value fails immediately with a
clear message. `SAP_CLIENT` defaults to `100`.

`.env` is listed in `.gitignore` and must not be committed.

## Usage

### Check the connection

```powershell
python check_connection.py
```

```
OK - connected to https://<subdomain>.abap.us10.hana.ondemand.com
     ADT discovery document is 2211 bytes
```

### Read source

```powershell
python read_abap.py class     ZCL_POC_REVIEW_DEMO
python read_abap.py interface ZIF_HELLO
python read_abap.py include   ZDEMO_INCLUDE
python read_abap.py fm        Z_READ_STUFF ZDEMO_FUGR

# write to a file instead of stdout
python read_abap.py class ZCL_POC_REVIEW_DEMO --out ZCL_POC_REVIEW_DEMO.abap
```

Object names are case-insensitive. Run the commands from the project folder so
`.env` is picked up.

Example output:

```abap
CLASS zcl_poc_review_demo DEFINITION
  PUBLIC FINAL CREATE PUBLIC.
  PUBLIC SECTION.
    INTERFACES if_oo_adt_classrun.
ENDCLASS.

CLASS ZCL_POC_REVIEW_DEMO IMPLEMENTATION.
  METHOD if_oo_adt_classrun~main.
    DATA lt_flight TYPE TABLE OF /dmo/flight.
    SELECT * FROM /dmo/flight INTO TABLE @lt_flight.

    LOOP AT lt_flight INTO DATA(ls_flight).
      SELECT SINGLE * FROM /dmo/carrier
        WHERE carrier_id = @ls_flight-carrier_id
        INTO @DATA(ls_carrier).
    ENDLOOP.

    out->write( 'Execution Finished' ).
  ENDMETHOD.
ENDCLASS.
```

## ADT endpoints

Reading source is a single `GET`; only the path changes per object type.

| Object    | ADT path |
|-----------|----------|
| Class     | `/sap/bc/adt/oo/classes/{name}/source/main` |
| Interface | `/sap/bc/adt/oo/interfaces/{name}/source/main` |
| Include   | `/sap/bc/adt/programs/includes/{name}/source/main` |
| Function  | `/sap/bc/adt/functions/groups/{group}/fmodules/{name}/source/main` |

## Implementation notes

- The access token is cached in memory and refreshed one minute before expiry,
  so a run that reads many objects authenticates once.
- `sap-client` is sent on every request.
- ADT returns source with `CRLF` line endings. `abap_session.py` normalises to
  `LF`; `read_abap.py` writes files with `newline="\n"`.

## Unattended jobs

This tool uses the password grant and needs a real BTP/ABAP login in `.env`,
which suits local use and the trial. For a scheduled job where storing a
personal password is not acceptable, the alternative is a communication user
with a Communication Arrangement and the `client_credentials` grant. That is a
separate setup and not covered here; on the trial the ADT source endpoints are
not reachable with a `client_credentials` token.

## Troubleshooting

| Symptom | Cause / fix |
|---------|-------------|
| `OAuth token request failed (401)` | Wrong `CLIENT_ID` / `CLIENT_SECRET` / `OAUTH_URL`, or wrong `ABAP_USERNAME` / `ABAP_PASSWORD`. |
| `403 for /sap/bc/adt/...` | The user lacks ADT / developer authorization for that object. |
| `Object not found` | Name typo, or the object is in a different system or client. |
| `Missing environment variable 'ABAP_HOST'` | `.env` not saved, or the command was run from the wrong folder. |
| Request hangs, then times out | `ABAP_HOST` wrong, or the trial system is stopped - restart it in the BTP cockpit. |

## Possible extensions

- A `search` command using `/sap/bc/adt/repository/informationsystem/search`.
- Resolving a package and reading all of its objects.
- Passing the source to another analysis tool.
