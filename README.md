# readabapcode

## Overview

`readabapcode` is a command-line utility that retrieves ABAP source code from an
SAP BTP ABAP Environment trial system without a graphical development
environment. It communicates with the ABAP Development Tools (ADT) REST API,
the same interface used by ADT in Eclipse, and authenticates non-interactively
through the OAuth 2.0 resource owner password credentials grant. No browser
session or single sign-on prompt is required.

The utility performs read operations only. It issues `GET` requests exclusively
and therefore cannot lock, modify, or delete any object in the target system.

## Repository contents

| File | Purpose |
|------|---------|
| `abap_session.py` | Acquisition and caching of the OAuth access token and a single authenticated `GET` helper. |
| `check_connection.py` | Verification of connectivity and authentication against the target system. |
| `read_abap.py` | Command-line interface for reading the source of a class, interface, include, or function module. |
| `.env.example` | Template for the required connection parameters. |
| `requirements.txt` | Python dependencies. |

## Prerequisites

- An SAP BTP ABAP Environment trial system ("ABAP Cloud Developer Trial"). The
  account used for authentication must hold developer authorization equivalent
  to that required for ADT in Eclipse.
- Python 3.9 or later.
- The Python packages `requests` and `python-dotenv`.

## Authentication model

ADT in Eclipse authenticates through a browser-based SAML flow, which is not
available to a non-interactive script. This utility instead requests a token
from the XSUAA instance associated with the ABAP system, using the OAuth 2.0
password grant:

1. A `POST` request is sent to `{OAUTH_URL}/oauth/token` containing:
   - `grant_type=password`;
   - the `username` and `password` of the BTP/ABAP developer account;
   - HTTP Basic authentication using the `clientid` and `clientsecret` from a
     service key.
2. XSUAA returns a bearer token that carries the developer's ABAP identity and
   authorizations.
3. Each subsequent ADT request includes the header
   `Authorization: Bearer <token>`.

Because the token represents a named user, no Communication Arrangement is
required. The user's existing developer authorizations govern access.

## Installation and configuration

### 1. Create a service key

In the SAP BTP cockpit, navigate to the subaccount, then to
**Instances and Subscriptions**, open the ABAP environment instance, and select
**Service Keys → Create**.

The following values are required from the service key:

| Service key field  | Environment variable |
|--------------------|----------------------|
| `url` (root)       | `ABAP_HOST`          |
| `uaa.url`          | `OAUTH_URL`          |
| `uaa.clientid`     | `CLIENT_ID`          |
| `uaa.clientsecret` | `CLIENT_SECRET`      |

The relevant section of a service key is structured as follows:

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

### 2. Install dependencies

```powershell
cd readabapcode
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### 3. Provide connection parameters

Copy `.env.example` to `.env` and supply the values:

```ini
ABAP_HOST=https://your-subdomain.abap.us10.hana.ondemand.com
OAUTH_URL=https://your-subdomain.authentication.us10.hana.ondemand.com
CLIENT_ID=your_client_id
CLIENT_SECRET=your_client_secret
SAP_CLIENT=100

ABAP_USERNAME=your_btp_username
ABAP_PASSWORD=your_btp_password
```

`ABAP_HOST`, `OAUTH_URL`, `CLIENT_ID`, `CLIENT_SECRET`, `ABAP_USERNAME`, and
`ABAP_PASSWORD` are mandatory. If any of them is absent, the utility terminates
immediately with a descriptive message. `SAP_CLIENT` is optional and defaults
to `100`.

The `.env` file contains credentials. It is excluded by `.gitignore` and must
not be committed to version control.

## Usage

### Verifying the connection

```powershell
python check_connection.py
```

Expected output:

```
OK - connected to https://<subdomain>.abap.us10.hana.ondemand.com
     ADT discovery document is 2211 bytes
```

### Reading source code

```powershell
python read_abap.py class     ZCL_POC_REVIEW_DEMO
python read_abap.py interface ZIF_HELLO
python read_abap.py include   ZDEMO_INCLUDE
python read_abap.py fm        Z_READ_STUFF ZDEMO_FUGR
```

To write the source to a file rather than standard output, supply the `--out`
option:

```powershell
python read_abap.py class ZCL_POC_REVIEW_DEMO --out ZCL_POC_REVIEW_DEMO.abap
```

Object names are case-insensitive. Commands must be executed from the project
directory so that the `.env` file is loaded.

### Example output

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

Retrieval of source code is performed with a single `GET` request. Only the
request path differs between object types.

| Object type | ADT path |
|-------------|----------|
| Class | `/sap/bc/adt/oo/classes/{name}/source/main` |
| Interface | `/sap/bc/adt/oo/interfaces/{name}/source/main` |
| Include | `/sap/bc/adt/programs/includes/{name}/source/main` |
| Function module | `/sap/bc/adt/functions/groups/{group}/fmodules/{name}/source/main` |

## Implementation notes

- The access token is held in memory and refreshed one minute before its
  expiry, so a session that reads many objects authenticates only once.
- The `sap-client` query parameter is included in every request.
- ADT returns source code with `CRLF` line endings. `abap_session.py`
  normalizes these to `LF`, and `read_abap.py` writes files using
  `newline="\n"`.

## Unattended operation

This utility relies on the password grant and therefore requires a valid
BTP/ABAP user account in the `.env` file, which is appropriate for local use
and for trial systems. For a scheduled process in which storing an individual
user's password is not acceptable, the alternative is a communication user
combined with a Communication Arrangement and the `client_credentials` grant.
That configuration is outside the scope of this project. On the trial landscape,
the ADT source endpoints are not accessible with a `client_credentials` token.

## Troubleshooting

| Symptom | Probable cause and resolution |
|---------|-------------------------------|
| `OAuth token request failed (401)` | Incorrect `CLIENT_ID`, `CLIENT_SECRET`, or `OAUTH_URL`, or incorrect `ABAP_USERNAME` or `ABAP_PASSWORD`. |
| `403 for /sap/bc/adt/...` | The user does not hold ADT or developer authorization for the requested object. |
| `Object not found` | The object name is misspelled, or the object resides in a different system or client. |
| `Missing environment variable 'ABAP_HOST'` | The `.env` file has not been saved, or the command was executed outside the project directory. |
| Request does not return and eventually times out | `ABAP_HOST` is incorrect, or the trial system is stopped and must be restarted in the SAP BTP cockpit. |
