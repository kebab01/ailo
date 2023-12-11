import logging
import requests
import json
import os
from dotenv import load_dotenv

load_dotenv()
logging.basicConfig(filename='ailo_session.log', level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s', datefmt='%Y-%m-%d %H:%M:%S')

# Constants
ENV_JSON_URL = "https://consumer-app.ailo.io/env.json"
LOGIN_URL = "https://login.ailo.io"
GATEWAY_URL = "https://gateway.ailo.io/consumer/graphql"


class AiloSession:

    def __init__(self, proxies=None):
        self.proxies = proxies or {}

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        pass

    def _get_auth0_client_id(self):
        try:
            response = requests.get(
                ENV_JSON_URL, proxies=self.proxies, verify=False)
            response.raise_for_status()

            return response.json().get("AUTH0_CLIENT_ID_MOBILE_PASSWORDLESS")
        except Exception as e:
            logging.error(f"Request failed for ur {response.ur} - {e}")
            raise

    def _get_login_cache(self):
        try:
            with open("login_cache.json", "r") as f:
                return json.load(f)
        except Exception as e:
            logging.error(f"Failed to load login cache - {e}")
            raise

    def _save_login_cache(self, data):
        try:
            with open("login_cache.json", "w") as f:
                json.dump(data, f)
        except Exception as e:
            logging.error(f"Opening cache file failed: {e}")
            raise

    def _refresh_token(self):
        login_cache = self._get_login_cache()
        auth0_client_id = self._get_auth0_client_id()

        try:
            response = requests.post(f"{LOGIN_URL}/oauth/token", json={
                "grant_type": "refresh_token",
                "client_id": auth0_client_id,
                "refresh_token": login_cache['refresh_token'],
            })
        except Exception as e:
            logging.error(f"Request failed for ur {response.ur} - {e}")
            raise

        self.BEARER_TOKEN = response.json()['access_token']
        self.on_startup()
        logging.info("Token refreshed")

    def login(self, email: str):
        if os.path.exists("login_cache.json"):
            print("Token exists, refreshing")
            self._refresh_token()
            return

        auth0_client_id = self._get_auth0_client_id()

        response = requests.post(f"{LOGIN_URL}/passwordless/start", json={
            "connection": "email",
            "client_id": auth0_client_id,
            "email": email,
            "send": "code"
        })

        input_code = input("Enter email code: ")

        response = requests.post(f"{LOGIN_URL}/oauth/token", json={
            "grant_type": "http://auth0.com/oauth/grant-type/passwordless/otp",
            "client_id": auth0_client_id,
            "username": email,
            "otp": input_code,
            "realm": "email",
            "audience": "https://app.ailo.io/",
            "scope": "openid profile email offline_access"
        })

        self._save_login_cache(response.json())
        self.BEARER_TOKEN = response.json()['access_token']
        self.on_startup()
        logging.info("New token aquired")

    def on_startup(self):
        """
            Gets the tenancy ID and rent amount
        """
        try:
            r = requests.post(f"{GATEWAY_URL}?op=getSetupData", proxies=self.proxies, verify=False, headers={
                "Authorization": f"Bearer {self.BEARER_TOKEN}"
            }, json={"operationName": "getSetupData", "variables": {}, "query": "query getSetupData {\n  companies {\n    __typename\n    id\n    ailoRN\n    registeredEntityName\n    registeredEntityId\n  }\n  tenancies {\n    items {\n      id\n      deposit {\n        id\n        status\n        amount {\n          cents\n          __typename\n        }\n        liability {\n          id\n          __typename\n        }\n        __typename\n      }\n      ailoRN\n      managementAiloRN\n      managementFolioAilorn\n      startDate\n      endDate\n      managingEntity {\n        id\n        timezone\n        registeredEntityName\n        organisationId\n        organisation {\n          id\n          name\n          effectiveUserContact {\n            id\n            ailorn\n            __typename\n          }\n          __typename\n        }\n        __typename\n      }\n      tenantships(pageCursor: {pageSize: 10000}) {\n        items {\n          tenantId\n          __typename\n        }\n        __typename\n      }\n      ...TenancyProperty\n      __typename\n    }\n    __typename\n  }\n  managements {\n    items {\n      id\n      ailoRN\n      endDate\n      managementAgreements {\n        items {\n          id\n          startDate\n          __typename\n        }\n        __typename\n      }\n      managementFolio {\n        id\n        ailorn\n        displayNumber {\n          id\n          code\n          __typename\n        }\n        __typename\n      }\n      ownerships {\n        ownerId\n        sharesOwned\n        __typename\n      }\n      managingEntity {\n        id\n        organisationId\n        timezone\n        organisation {\n          id\n          name\n          effectiveUserContact {\n            id\n            ailorn\n            __typename\n          }\n          __typename\n        }\n        __typename\n      }\n      ...ManagementProperty\n      __typename\n    }\n    __typename\n  }\n  effectiveUser {\n    id\n    onboardingCompletedAt\n    organisations {\n      id\n      availableFeatures {\n        id\n        __typename\n      }\n      unavailableFeatureIds\n      __typename\n    }\n    person {\n      __typename\n      id\n      ailoRN\n      firstName\n      lastName\n      emailAddress\n      photo {\n        id\n        url\n        thumbnailUrl\n        __typename\n      }\n    }\n    __typename\n  }\n}\n\nfragment TenancyProperty on Tenancy {\n  id\n  property {\n    ...PropertyIdAndAddress\n    __typename\n  }\n  __typename\n}\n\nfragment PropertyIdAndAddress on Property {\n  id\n  address {\n    ...Address\n    __typename\n  }\n  __typename\n}\n\nfragment Address on Address {\n  unitStreetNumber\n  streetName\n  suburb\n  state\n  postcode\n  country\n  __typename\n}\n\nfragment ManagementProperty on Management {\n  id\n  ailorn: ailoRN\n  property {\n    ...PropertyIdAndAddress\n    __typename\n  }\n  __typename\n}\n"})
            r.raise_for_status()
        except Exception as e:
            logging.error(f"Request failed for ur {r.url} - {e}")
            raise

        result = r.json()
        tenancy = result['data']['tenancies']['items'][0]
        self.tenant_id = tenancy['id']
        self.rent_amount = tenancy['deposit']['amount']['cents']
        self.legal_entity_id = result['data']['effectiveUser']['person']['ailoRN']
        self.getRentDetails()
        logging.info("Got startup details")

    def getRentDetails(self):

        try:
            r = requests.post(f"{GATEWAY_URL}?op=getTenancyRentOwing", proxies=self.proxies, verify=False, headers={
                "Authorization": f"Bearer {self.BEARER_TOKEN}"
            }, json={"operationName": "getTenancyRentOwing", "variables": {"tenancyId": self.tenant_id, "payerLegalEntityId": f"{self.legal_entity_id}", "cursor": None, "pageSize": 20}, "query": "query getTenancyRentOwing($tenancyId: ID!, $payerLegalEntityId: AiloRN!, $businessTransactionId: AiloRN, $cursor: String, $pageSize: Int!) {\n  tenancy(tenancyId: $tenancyId) {\n    id\n    liability {\n      id\n      ...liabilityAutoPaymentDetails\n      paymentPlans(payerLegalEntityId: $payerLegalEntityId, enabled: true) {\n        pageInfo {\n          total\n          __typename\n        }\n        __typename\n      }\n      __typename\n    }\n    rent {\n      id\n      ailoRN\n      reference\n      timezone\n      owingEvents(\n        filter: {businessTransactionAilorn: $businessTransactionId}\n        pagination: {pageSize: 1}\n      ) {\n        items {\n          id\n          paidTo {\n            effective {\n              date\n              __typename\n            }\n            __typename\n          }\n          __typename\n        }\n        __typename\n      }\n      progress {\n        paidTo {\n          effective {\n            date\n            partPayment {\n              cents\n              __typename\n            }\n            __typename\n          }\n          __typename\n        }\n        overdue {\n          amount {\n            total {\n              cents\n              __typename\n            }\n            __typename\n          }\n          __typename\n        }\n        due {\n          date\n          __typename\n        }\n        nextDue {\n          date\n          amount {\n            total {\n              cents\n              __typename\n            }\n            __typename\n          }\n          __typename\n        }\n        endOfOwing {\n          amount {\n            total {\n              cents\n              __typename\n            }\n            __typename\n          }\n          date\n          __typename\n        }\n        __typename\n      }\n      history(paginationParams: {cursor: $cursor, pageSize: $pageSize}) {\n        pageInfo {\n          total\n          hasNext\n          hasPrevious\n          nextCursor\n          __typename\n        }\n        items {\n          ... on PaymentOwingHistoryListItem {\n            id\n            cause {\n              id\n              ailoRN\n              interaction {\n                type\n                statusDetails {\n                  currentStatus\n                  __typename\n                }\n                __typename\n              }\n              __typename\n            }\n            __typename\n          }\n          ... on AdjustmentOwingHistoryListItem {\n            id\n            __typename\n          }\n          ... on ChargeCycleOwingHistoryListItem {\n            id\n            __typename\n          }\n          __typename\n        }\n        __typename\n      }\n      __typename\n    }\n    endDate\n    __typename\n  }\n}\n\nfragment liabilityAutoPaymentDetails on Liability {\n  autoPaymentDetails {\n    paymentMethod {\n      id\n      __typename\n    }\n    __typename\n  }\n  __typename\n}\n"})
            r.raise_for_status()
        except Exception as e:
            logging.error(f"Request failed for ur {r.url} - {e}")
            raise

        result = r.json()

        self.liability_id = result['data']['tenancy']['liability']['id']
        self.rent_id = result['data']['tenancy']['rent']['id']
        self.next_due = result['data']['tenancy']['rent']['progress']['nextDue']['date']
        self.amount_due = result['data']['tenancy']['rent']['progress']['nextDue']['amount']['total']['cents']

        try:
            r = requests.post(f"{GATEWAY_URL}?op=getPayRentLiabilityDetails", proxies=self.proxies, verify=False, headers={
                "Authorization": f"Bearer {self.BEARER_TOKEN}"
            }, json={"operationName": "getPayRentLiabilityDetails", "variables": {"tenancyId": self.tenant_id, "liabilityId": self.liability_id}, "query": "query getPayRentLiabilityDetails($tenancyId: ID!, $liabilityId: ID!) {\n  liabilityById(liabilityId: $liabilityId) {\n    id\n    reference\n    paymentKey\n    ...liabilityAutoPaymentDetails\n    __typename\n  }\n  tenancy(tenancyId: $tenancyId) {\n    id\n    endDate\n    rent {\n      id\n      ailoRN\n      progress {\n        endOfOwing {\n          amount {\n            total {\n              cents\n              __typename\n            }\n            __typename\n          }\n          date\n          __typename\n        }\n        __typename\n      }\n      __typename\n    }\n    bond {\n      id\n      amountOwing {\n        cents\n        __typename\n      }\n      __typename\n    }\n    __typename\n  }\n}\n\nfragment liabilityAutoPaymentDetails on Liability {\n  autoPaymentDetails {\n    paymentMethod {\n      id\n      __typename\n    }\n    __typename\n  }\n  __typename\n}\n"})

            r.raise_for_status()

        except Exception as e:
            logging.error(f"Request failed for ur {r.url} - {e}")
            raise

        result = r.json()
        self.payment_key = result['data']['liabilityById']['paymentKey']
        logging.info("Got rent details")

    def addTempBankAcc(self, accountName: str, accountNumber: int, bsb: str):

        print(f"Adding temporary bank account for {accountName} {accountNumber} {bsb}")
        try:
            r = requests.post(f"{GATEWAY_URL}?op=addBankAccount", proxies=self.proxies, verify=False, headers={
                "Authorization": f"Bearer {self.BEARER_TOKEN}"
            }, json={"operationName": "addBankAccount", "variables": {"owner": f"{self.legal_entity_id}", "details": {"accountName": accountName, "accountNumber": accountNumber, "bsb": bsb, "onceOff": True}}, "query": "mutation addBankAccount($owner: AiloRN!, $details: BankAccountInput!) {\n  addBankAccount(owner: $owner, details: $details) {\n    id\n    accountName\n    accountNumber\n    __typename\n  }\n}\n"})

            r.raise_for_status()
        except Exception as e:
            logging.error(f"Request failed for ur {r.url} - {e}")
            raise
        result = r.json()
        self.bank_account_id = result['data']['addBankAccount']['id']
        logging.info("Added temporary bank account")

    def pay_liability(self, amount: int, payment_key: str, liability_id: str, bank_account_id: str):

        try:
            r = requests.post(f"{GATEWAY_URL}?op=payLiability", proxies=self.proxies, verify=False, headers={
                "Authorization": f"Bearer {self.BEARER_TOKEN}"
            }, json={"operationName": "payLiability", "variables": {"amount": {"cents": amount}, "idempotentKey": payment_key, "liabilityId": liability_id, "paymentMethodId": bank_account_id}, "query": "mutation payLiability($amount: MoneyInput!, $idempotentKey: GeneratedKey!, $liabilityId: ID!, $paymentMethodId: ID!) {\n  payLiability(\n    amount: $amount\n    idempotentKey: $idempotentKey\n    liabilityId: $liabilityId\n    paymentMethodId: $paymentMethodId\n  ) {\n    status\n    businessTransaction {\n      id\n      createdAt\n      __typename\n    }\n    businessTransactionId\n    __typename\n  }\n}\n"})
            r.raise_for_status()

            print(r.json())
        except Exception as e:
            logging.error(f"Request failed for ur {r.url} - {e}")
            raise
        result = r.json()
        logging.info("Successfully paid rent")    


def main():
    with AiloSession() as a:
        a.login(os.getenv("EMAIL"))
        a.getRentDetails()
        a.addTempBankAcc(os.getenv("ACCOUNT_NAME"), os.getenv(
        "ACCOUNT_NUMBER"), os.getenv("BSB"))
        a.pay_liability(0, a.payment_key, a.liability_id, a.bank_account_id)

if __name__ == "__main__":
    main()
