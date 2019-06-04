# Payments

## API

- Checking available products (ATM rents) for resources

    Resources have `products` field that contains a list of the resource's products.

    Example response (GET `/v1/resource/`):

    ```json
    ...

    "products": [
        {
            "id": "awevmfmr3w5a",
            "type": "rent",
            "name": {
                "fi": "testivuokra",
                "en": "test rent"
            },
            "description": {
                "fi": "Testivuokran kuvaus.",
                "en": "Test rent description."
            },
            "tax_percentage": "24.00",
            "price": "12.40",
            "price_type": "per_hour"
        }
    ],
    ...
    ```

    At least for now, when there is a `rent` type product available, and there should be only one of those at a time, it should be ordered and paid in order to create a successful reservation.

    Currently `rent` is the only `type` option, but there will be new ones in the future.

    Currently `per_hour` is the only `price_type` option, but there will be new ones in the future.

- Creating an order

    Order endpoint is used to create an order of product(s).

    Example request (POST `/v1/order/`):

    ```json
    {
        "reservation": 191999,
        "order_lines": [
            {
                "product": "awemfcd2iqlq",
                "quantity": 1
            }
        ],
        "payer_first_name": "Ville",
        "payer_last_name": "Virtanen",
        "payer_email_address": "ville@virtanen.com",
        "payer_address_street": "Virtatie 5",
        "payer_address_zip": "55555",
        "payer_address_city": "Virtala",
        "return_url": "https://varaamo.hel.fi/payment-return-url/"
    }
    ```

    `return_url` is the URL where the user's browser will be redirected after the payment process. Typically it should be some kind of "payment done" view in the UI.

    `quantity` can be omitted when it is 1 (and for rents it probably should always be).

    Example response:

    ```json
    {
        "id": 59,
        "order_lines": [
            {
                "product": {
                    "id": "awemfcd2iqlq",
                    "type": "rent",
                    "name": {
                        "fi": "testivuokra"
                    },
                    "description": {
                        "fi": "testikuvaus"
                    },
                    "tax_percentage": "24.00",
                    "price": "12.40",
                    "price_type": "per_hour"
                },
                "quantity": 1,
                "price": "18.60"
            }
        ],
        "price": "18.60",
        "payment_url": "https://payform.bambora.com/pbwapi/token/d02317692040937087a4c04c303dd0da14441f6f492346e40cea8e6a6c7ffc7c",
        "status": "waiting",
        "order_number": "awemfcd2icdcd",
        "payer_first_name": "Ville",
        "payer_last_name": "Virtanen",
        "payer_email_address": "ville@virtanen.com",
        "payer_address_street": "Virtatie 5",
        "payer_address_zip": "55555",
        "payer_address_city": "Virtala",
        "reservation": 191999
    }
    ```

    After a successful order creation, the UI should redirect the user to the URL in `payment_url` in order to start a payment process.

- Checking prices of orders

    Price checking endpoint can be used to check the price of an order without actually creating the order.

    Example request (POST `/v1/order/check_price/`):

    ```json
    {
        "begin": "2019-04-11T08:00:00+03:00",
        "end": "2019-04-11T11:00:00+03:00",
        "order_lines": [
            {
                "product": "awemfcd2iqlq",
                "quantity": 5
            }
        ]
    }
    ```

    Example response:

    ```json
    {
        "order_lines": [
            {
                "product": {
                    "id": "awemfcd2iqlq",
                    "type": "rent",
                    "name": {
                        "fi": "testivuokra"
                    },
                    "description": {
                        "fi": "testikuvaus"
                    },
                    "tax_percentage": "24.00",
                    "price": "12.40",
                    "price_type": "per_hour"
                },
                "quantity": 5,
                "price": "186.00"
            }
        ],
        "price": "186.00",
        "begin": "2019-04-11T08:00:00+03:00",
        "end": "2019-04-11T11:00:00+03:00"
    }
    ```
