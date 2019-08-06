
## Analitico Billing

Analitico's billing flows are implemented using Stripe Checkout and Stripe billing.

### Billing APIs

Showing available plans  
```GET /api/billing/plans```

Retrieving updated information on a workspace subscription:  
```GET /api/billing/ws_xxx/subscription```

Cancelling a subscription plan:  
```DELETE /api/billing/ws_xxx/subscription```

Changing a subscription plan:  
```POST /api/billing/ws_xxx/subscription/plan/plan_xxx```

Showing invoices related to a workspace:  
```GET /api/billing/ws_xxx/invoices```


### Purchasing a plan

First you create a session for the current user:  
`POST /api/billing/sessions`

The you use the sessionId from the newly created session to redirect to checkout:  
```html
<!-- Load Stripe.js on your website. -->
<script src="https://js.stripe.com/v3"></script>

<!-- Create a button that your customers click to complete their purchase. Customize the styling to suit your branding. -->
<button role="link">Checkout</button>
<div id="error-message"></div>
<script>
  var stripe = Stripe('pk_test_rRLjkYNvCrUl4e6UOMh7Iybh');
  var checkoutButton = document.getElementById('checkout-button-plan_premium_usd');
  checkoutButton.addEventListener('click', function () {
    // When the customer clicks on the button, redirect them to Checkout.
    stripe.redirectToCheckout({
      sessionId: 'cs_test_p8SWDpxdds64PHlrxSEp7CL53cHb3vrPTrBOqUWHswS34yAdg682lsjk',
    })
    .then(function (result) {
      if (result.error) {
        // If `redirectToCheckout` fails due to a browser or network
        // error, display the localized error message to your customer.
        var displayError = document.getElementById('error-message');
        displayError.textContent = result.error.message;
      }
    });
  });
</script>
```

### Events

Example of events flow to create a subscription:

customer.created (test)  
https://dashboard.stripe.com/test/events/evt_1F44YwAICbSiYX9YpEy8r6Pg

payment_method.attached (test)  
https://dashboard.stripe.com/test/events/evt_1F44YwAICbSiYX9YtLLsxJET

setup_intent.created (test)  
https://dashboard.stripe.com/test/events/evt_1F44YwAICbSiYX9Yvi0UeKp6

setup_intent.succeeded (test)  
https://dashboard.stripe.com/test/events/evt_1F44YwAICbSiYX9YJo1S2AJE

invoice.created (test)  
https://dashboard.stripe.com/test/events/evt_1F44YwAICbSiYX9YFu6SBngY

customer.updated (test)  
https://dashboard.stripe.com/test/events/evt_1F44YxAICbSiYX9YRqEfkouH

customer.subscription.created (test)  
https://dashboard.stripe.com/test/events/evt_1F44YxAICbSiYX9YTzuuGI1y

invoice.finalized (test)  
https://dashboard.stripe.com/test/events/evt_1F44YxAICbSiYX9Y2dMecaKj

invoice.updated (test)  
https://dashboard.stripe.com/test/events/evt_1F44YxAICbSiYX9Ye9fON4Uw

invoice.payment_succeeded (test)  
https://dashboard.stripe.com/test/events/evt_1F44YyAICbSiYX9YNAuSTXjT

checkout.session.completed (test)  
https://dashboard.stripe.com/test/events/evt_1F44YyAICbSiYX9YdqLcjLoA

