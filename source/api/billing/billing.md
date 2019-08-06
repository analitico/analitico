
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
