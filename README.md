# Ailo Payment Automation

[Ailo](https://ailo.io/) is a property management platform that some Real Estate agents such as [Ray White](https://www.raywhite.com/) mandate that their tenants use to pay rent. Ailo charges a transaction fee if you wish to save your bank details or set up reoccurring payments. I personally think this should be illegal as they have taken what was a fee free system of sending the money directly to the agent via a BSB and Account number and now charges tenants a fee for the Real Estate Agents convenience. In response to this, I reverse-engineered their API and created this script to run automatically and pay rent for me by adding a temporary bank account (which avoids their fee system) and then pay the rent. Please add your contributions to this repository if you have any ideas on how to improve this script.

## Prerequisites

Before using this script, ensure you have the following:

- Python 3.x installed on your system.
- Required Python packages installed. You can install them using:

```bash
    pip install requests python-dotenv
```

- A valid Ailo account and API access.

## Getting Started

1. Clone or download the repository to your local machine.

```bash
    git clone https://github.com/kebab01/ailo
```

2. Create a virtual environment (optional but recommended):
3. 
```bash
    python -m venv venv
    source venv/bin/activate   # On Windows: venv\Scripts\activate
```

1. Install the required dependencies:

```bash
    pip install -r requirements.txt
```

4. Create a .env file in the project root and add your Ailo credentials:

```bash
   EMAIL=your_email@example.com
   ACCOUNT_NAME=your_account_name
   ACCOUNT_NUMBER=your_account_number
   BSB=your_bsb
```

5. Create a cron job to run the script at a specified time. For example, to run the script on wednesday each week at 8am you would add the following to your crontab:

```bash
    0 8 * * 3 /path/to/venv/bin/python /path/to/ailo/main.py
```

## Usage

Make a payment using the Ailo API

```python
    from ailo import AiloSession

    with AiloSession() as a:
        a.login(os.getenv("EMAIL"))
        a.getRentDetails()
        a.addTempBankAcc(os.getenv("ACCOUNT_NAME"), os.getenv(
        "ACCOUNT_NUMBER"), os.getenv("BSB"))
        a.pay_liability(0, a.payment_key, a.liability_id, a.bank_account_id)
```