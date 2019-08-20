# Payments

Payments app adds support for Respa resources to have paid reservations. In addition to requiring a mandatory rent for a resource's usage, it is also possible to offer optional extra accessories to be ordered and paid (not yet supported in Varaamo).

Transactions are handled by a third party payment provider. Currently implemented provider integrations:

* [Bambora Payform](https://www.bambora.com/fi/fi/online/)

## Enabling and configuring Payments

There are a couple of required configuration keys that need to be set in order to enable the payments and the third party provider currently in use:

- `RESPA_PAYMENTS_ENABLED`: Whether payments are enabled or not. Boolean `True`/`False`. The default value is `False`.
- `RESPA_PAYMENTS_PROVIDER_CLASS`: Dotted path to the active provider class e.g. `payments.providers.BamboraPayformProvider` as a string. No default value.
- `RESPA_PAYMENTS_PAYMENT_WAITING_TIME`: In minutes, how old the potential unpaid orders/reservations have to be in order for Respa cleanup to set them expired. The default value is `15`.

`./manage.py expire_too_old_unpaid_orders` runs the order/reservation cleanup for current orders. You'll probably want to run it periodically at least in production. [Cron](https://en.wikipedia.org/wiki/Cron) is one candidate for doing that.

### Bambora Payform configuration

The Bambora API version the provider implementation targets is `w3.1`. More information about the API can be found in [Bambora's official API documentation](https://payform.bambora.com/docs/web_payments/?page=full-api-reference) page.

In addition to the general configuration keys mentioned in the previous section, enabling Bambora also requires some extra configuration to function:

- `RESPA_PAYMENTS_BAMBORA_API_URL`: Optionally override the base URL where Bambora requests are sent. Defaults to the documented Bambora endpoint.
- `RESPA_PAYMENTS_BAMBORA_API_KEY`: Identifies which merchant store account to use with Bambora. Value can be found in the merchant portal. Provided as a string. No default value.
- `RESPA_PAYMENTS_BAMBORA_API_SECRET`: Used to calculate hashes out of the data being sent and received, to verify it is not being tampered with. Also found in the merchant portal and provided as a string. No default value.
- `RESPA_PAYMENTS_BAMBORA_PAYMENT_METHODS`: An array of payment methods to show to the user to select from e.g.`['nordea', 'creditcards']`. Full list of supported values can be found in [the currencies section of](https://payform.bambora.com/docs/web_payments/?page=full-api-reference#currencies) Bambora's API documentation page.

## Basics

Model `Product` represents everything that can be ordered and paid alongside a reservation. Products are linked to one or multiple resources.

There are currently two types of products:

- `rent`: At least one product of type `rent` must be ordered when such is available on the resource. 

- `extra`: Ordering of products of type `extra` is not mandatory, so when there are only `extra` products available, one can create a reservation without an order. However, when an order is created, even with just extra product(s), it must be paid to get the reservation confirmed.

Everytime a product is saved, a new copy of it is created in the db, so product modifying does not affect already existing orders.

All prices are in euros. A product's price is stored in `price` field. However, there are different ways the value should be interpreted depending on `price_type` field's value: 

- `fixed`: The price stays always the same regardless of the reservation, so if `price` is `10.00` the final price is 10.00 EUR.

- `per_period`: When price type is `per_period`, field `price_period` contains length of the period, for example if `price` is `10.00` and `price_period` is `00:30:00` it means the actual price is 10.00 EUR / 0.5h

Model `Order` represents orders of products. One and only one order is linked to exactly one reservation.

An order can be in state `waiting`, `confirmed`, `rejected`, `expired` or `cancelled`. A new order will start from state `waiting`, and from there it will change to one of the other states. Only valid other state change is from `confirmed` to `cancelled`.

An order is created by providing its data in `order` field when creating a reservation via the API. The UI must also provide a return URL to which the user will be redirected after the payment process has been completed. In the creation response the UI gets back a payment URL, to which it must redirect the user to start the actual payment process. 

## Administration

Currently Django Admin needs to be used for all administrative tasks, ie. adding / modifying / deleting products, and viewing / cancelling orders.

## Permissions

- By default it is not possible to modify reservations that have an order using the API. Permission to modify a paid reservation can be granted using resource permission `can_modify_paid_reservation`.

- Everyone can see only their own orders' data in the API. With resource permission `can_view_reservation_product_orders` one can view all other users' order data as well.

## API usage

### Checking available products

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
        "price": "10.00",
        "price_type": "per_period",
        "price_period": "01:00:00",
        "max_quantity": 1
    }
],

...
```

### Checking the price of an order

Price checking endpoint can be used to check the price of an order without actually creating the order.

Example request (POST `/v1/order/check_price/`):

```json
{
    "begin": "2019-04-11T08:00:00+03:00",
    "end": "2019-04-11T10:00:00+03:00",
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
                "type": "extra",
                "name": {
                    "fi": "testituote"
                },
                "description": {
                    "fi": "testituotteen kuvaus"
                },
                "tax_percentage": "24.00",
                "price": {
                    "type": "per_period",
                    "tax_percentage": "24.00",
                    "amount": "10.00",
                    "period": "01:00:00",
                }
                "max_quantity": 10
            },
            "quantity": 5,
            "unit_price": "20.00",
            "price": "100.00"
        }
    ],
    "price": "100.00",
    "begin": "2019-04-11T08:00:00+03:00",
    "end": "2019-04-11T11:00:00+03:00"
}
```

A product's `price` always has `type` field. Existence of other fields depends on the type:

* when the type is `fixed`, there are also fields `tax_percentage` and `amount`
* when the type is `per_period`, there are also fields `tax_percentage`, `amount` and `period`

### Creating an order

Orders are created by creating a reservation normally and including additional `order` field which contains the order's data.

Example request (POST `/v1/reservation/`):

```json
{
    "resource": "av3jzamoxkva",
    "begin": "2019-10-07T11:00:00+03:00",
    "end": "2019-10-07T13:30:00+03:00",
    "event_subject": "kemut",
    "billing_first_name": "Ville",
    "billing_last_name": "Virtanen",
    "billing_phone_number": "555-123456",
    "order": {
        "order_lines": [
            {
                "product": "awevmfmr3w5a",
                "quantity": 1
            }
        ],
        "return_url": "https://varaamo.hel.fi/payment-return-url/"
    }
}
```

`return_url` is the URL where the user's browser will be redirected after the payment process. Typically it should be some kind of "payment done" view in the UI.

`quantity` can be omitted when it is 1.

Example response:

```json
...

"order":
    {
        "id": "awemfcd2icdcd",
        "order_lines": [
            {
                "product": {
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
                    "price": {
                        "type": "per_period",
                        "tax_percentage": "24.00",
                        "amount": "10.00",
                        "period": "01:00:00",
                    }
                    "max_quantity": 1
                },
                "quantity": 1,
                "unit_price": "20.00",
                "price": "20.00"
            }
        ],
        "price": "20.00",
        "payment_url": "https://payform.bambora.com/pbwapi/token/d02317692040937087a4c04c303dd0da14441f6f492346e40cea8e6a6c7ffc7c",
        "status": "waiting"
    }

...
```

After a successful order creation, the UI should redirect the user to the URL in `payment_url` in order to start a payment process. Once the payment has been carried out, the user is redirected to the return url given when creating the order. The return url will also contain query params `payment_status=<success or failure>` and `reservation_id=<ID of the reservation in question>`.

Example full return url: `https://varaamo.hel.fi/payment-return-url/?payment_status=success&reservation_id=59535434`

### Modifying an order

Modifying an order is not possible, and after a reservation's creation the `order` field is read-only.

### Order data in reservation API endpoint

Reservation data in the API includes `order` field when the current user has permission to view it (either own reservation or via the explicit view order permission).

Example response (GET `/v1/reservation/`):

```json
...

"order": "awemfcd2icdcd",

...
```

Normally when fetching a list of reservations, `order` field contains only the order ID of the order. It is also possible to request for the whole order data by adding query param `include=order_detail` to the request.

Example response (GET `/v1/reservation/?include=order_detail`):

```json
...

"order":
    {
        "id": "awemfcd2icdcd",
        "order_lines": [
            {
                "product": {
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
                    "price": {
                        "type": "per_period",
                        "tax_percentage": "24.00",
                        "amount": "10.00",
                        "period": "01:00:00",
                    }
                    "max_quantity": 1
                },
                "quantity": 1,
                "unit_price": "20.00",
                "price": "20.00"
            }
        ],
        "price": "20.00",
        "status": "confirmed"
    }

...
```

## Adding a new provider

Core functionality of the provider implementation is to first prepare the transaction with the payment provider API, which in Bambora's case means posting the `Order` data there and getting a payment token back to be used as part of the payment URL the customer is redirected to. Second is to handle the customer returning from paying the `Order`, extracting and storing the state and redirecting the customer to the correct destination.

Key steps when adding support for a new provider:

1. Extend and implement `PaymentProvider` base class from `payments.providers.base`
2. Provide a value for the `RESPA_PAYMENTS_PROVIDER_CLASS` configuration key, which is a dotted path to the active provider class

### Configuring the provider

Active payment provider is initialized in providers package init. Before initializing, a static function named `get_config_template()` is called that returns a dict containing the provider specific `key: value type` or `key: (value type, default value)` -items, for example:

```python
return {
    RESPA_PAYMENTS_API_URL: (str, 'https://my_awesome_provider/api'),
    RESPA_PAYMENTS_API_KEY: str,
}
```

Values for these configuration keys are read from either `settings` or `.env`. The base provider constructor then receives the fully loaded configuration and the template keys with their values are usable through `self.config` class variable in the provider.

### Overridable methods

The minimum a new provider implementation needs to implement are these methods:

#### initiate_payment(order)

Starts the payment process by preparing the `Order` to be paid. This might mean posting information about the `Order` to the provider API or just constructing a URL using the data and provider specific API identifiers. Whatever the case, returns the URL where Respa redirects the customer to pay the order. Request object is available as `self.request`.

Respa acts as a mediator between the payment provider and the UI, `request` and `ui_return_url` are needed for creating the correct redirect chain. `get_success_url()` from base creates the success handler URL and by default `ui_return_url` is added to that as an extra query parameter. There is a `handle_failure_request()` -call that can also be overridden if the provider uses a separate callback for failed payments and a `handle_notify_request()` if the provider supports an asynchronous callback.

#### handle_success_request()

When customer has completed the payment, the provider redirects back to this success handler where the payment status is checked. With Bambora, this means extracting query parameters from the URL, checking they haven't been tampered with and marking the `Order` state to reflect the status code. Request object is available as `self.request`.

After the status has been checked, the customer is redirected to the `ui_return_url` that was provided when `Order` was prepared, with additional `payment_status` query parameter stating whether the process was a `success` or a `failure` and an `order_id` parameter.

## Diagrams

### Data structure

![payments models](payments_models.png "payments models")

### Payment flow

![payments flow](payment_flow.png "payments flow")
