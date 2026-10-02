"use strict";

/* =========================================================
   ZALIVIO FOODS - CHECKOUT PAGE
========================================================= */


/* =========================================================
   LOAD CART FROM LOCAL STORAGE
========================================================= */

let cart = [];

try {

    const savedCart =
        localStorage.getItem(
            "zalivioCart"
        );


    if (savedCart) {

        const parsedCart =
            JSON.parse(savedCart);


        if (Array.isArray(parsedCart)) {

            cart = parsedCart;
        }
    }

} catch (error) {

    console.error(
        "Unable to load cart:",
        error
    );

    cart = [];
}


/* =========================================================
   WAIT FOR PAGE
========================================================= */

document.addEventListener(
    "DOMContentLoaded",
    function () {


        /* =================================================
           PAGE ELEMENTS
        ================================================= */

        const checkoutContent =
            document.getElementById(
                "checkout-content"
            );

        const emptyCheckout =
            document.getElementById(
                "empty-checkout"
            );

        const checkoutItems =
            document.getElementById(
                "checkout-items"
            );

        const subtotalElement =
            document.getElementById(
                "checkout-subtotal"
            );

        const deliveryElement =
            document.getElementById(
                "checkout-delivery"
            );

        const totalElement =
            document.getElementById(
                "checkout-total"
            );

        const checkoutForm =
            document.getElementById(
                "checkout-form"
            );

        const placeOrderButton =
            document.getElementById(
                "place-order-button"
            );

        const checkoutMessage =
            document.getElementById(
                "checkout-message"
            );

        /* =================================================
           REQUIRED ELEMENT CHECK
        ================================================= */

        if (
            !checkoutContent ||
            !emptyCheckout ||
            !checkoutItems ||
            !subtotalElement ||
            !deliveryElement ||
            !totalElement
        ) {

            console.error(
                "Required checkout elements are missing from checkout.html."
            );

            return;
        }


        /* =================================================
           FORMAT PRICE
        ================================================= */

        function formatPrice(amount) {

            return "₹" +
                Number(amount).toFixed(0);
        }


        /* =================================================
           SHOW MESSAGE
        ================================================= */

        function showMessage(
            message,
            type = "error"
        ) {

            if (!checkoutMessage) {
                return;
            }


            checkoutMessage.textContent =
                message;


            checkoutMessage.className =
                "checkout-message " +
                type;
        }


        /* =================================================
           CLEAR MESSAGE
        ================================================= */

        function clearMessage() {

            if (!checkoutMessage) {
                return;
            }


            checkoutMessage.textContent =
                "";


            checkoutMessage.className =
                "checkout-message";
        }


        /* =================================================
           VALIDATE CART
        ================================================= */

        function getValidCart() {

            if (!Array.isArray(cart)) {
                return [];
            }


            return cart.filter(
                function (item) {

                    if (
                        !item ||
                        !item.name
                    ) {
                        return false;
                    }


                    const price =
                        Number(item.price);

                    const quantity =
                        Number(item.quantity);


                    if (
                        !Number.isFinite(price) ||
                        price < 0
                    ) {
                        return false;
                    }


                    if (
                        !Number.isInteger(
                            quantity
                        ) ||
                        quantity < 1
                    ) {
                        return false;
                    }


                    return true;
                }
            );
        }


        /* =================================================
           RENDER CHECKOUT
        ================================================= */

        function renderCheckout() {

            cart =
                getValidCart();


            /* ---------------------------------------------
               EMPTY CART
            --------------------------------------------- */

            if (cart.length === 0) {

                checkoutContent.style.display =
                    "none";


                emptyCheckout.classList.add(
                    "active"
                );


                return;
            }


            /* ---------------------------------------------
               SHOW CHECKOUT
            --------------------------------------------- */

            checkoutContent.style.display =
                "grid";


            emptyCheckout.classList.remove(
                "active"
            );


            checkoutItems.innerHTML =
                "";


            let subtotal = 0;


            /* ---------------------------------------------
               RENDER PRODUCTS
            --------------------------------------------- */

            cart.forEach(
                function (item) {

                    const price =
                        Number(item.price);

                    const quantity =
                        Number(item.quantity);

                    const itemTotal =
                        price * quantity;


                    subtotal +=
                        itemTotal;


                    const productElement =
                        document.createElement(
                            "div"
                        );


                    productElement.className =
                        "checkout-item";


                    /* Product image */

                    const image =
                        document.createElement(
                            "img"
                        );


                    image.src =
                        "/static/images/" +
                        encodeURIComponent(
                            item.image || ""
                        );


                    image.alt =
                        item.name;


                    /* Product information */

                    const productDetails =
                        document.createElement(
                            "div"
                        );


                    const productName =
                        document.createElement(
                            "h3"
                        );


                    productName.textContent =
                        item.name;


                    const productQuantity =
                        document.createElement(
                            "p"
                        );


                    productQuantity.textContent =
                        formatPrice(price) +
                        " × " +
                        quantity;


                    productDetails.appendChild(
                        productName
                    );


                    productDetails.appendChild(
                        productQuantity
                    );


                    /* Product total */

                    const productPrice =
                        document.createElement(
                            "span"
                        );


                    productPrice.className =
                        "checkout-item-price";


                    productPrice.textContent =
                        formatPrice(
                            itemTotal
                        );


                    /* Add to page */

                    productElement.appendChild(
                        image
                    );


                    productElement.appendChild(
                        productDetails
                    );


                    productElement.appendChild(
                        productPrice
                    );


                    checkoutItems.appendChild(
                        productElement
                    );
                }
            );


            /* ---------------------------------------------
               CALCULATE TOTAL
            --------------------------------------------- */

            const deliveryCharge =
                subtotal >= 499
                    ? 0
                    : 49;


            const total =
                subtotal +
                deliveryCharge;


            subtotalElement.textContent =
                formatPrice(
                    subtotal
                );


            deliveryElement.textContent =
                deliveryCharge === 0
                    ? "FREE"
                    : formatPrice(
                        deliveryCharge
                    );


            totalElement.textContent =
                formatPrice(
                    total
                );
        }


        /* =================================================
           CHECKOUT FORM
        ================================================= */

        if (checkoutForm) {

            checkoutForm.addEventListener(
                "submit",
                async function (event) {

                    event.preventDefault();


                    clearMessage();


                    /* -------------------------------------
                       CHECK CART
                    ------------------------------------- */

                    cart =
                        getValidCart();


                    if (
                        cart.length === 0
                    ) {

                        showMessage(
                            "Your cart is empty."
                        );

                        return;
                    }


                    /* -------------------------------------
                       HTML FORM VALIDATION
                    ------------------------------------- */

                    if (
                        !checkoutForm.checkValidity()
                    ) {

                        checkoutForm.reportValidity();

                        return;
                    }


                    /* -------------------------------------
                       FORM ELEMENTS
                    ------------------------------------- */

                    const nameInput =
                        document.getElementById(
                            "customer_name"
                        );

                    const emailInput =
                        document.getElementById(
                            "email"
                        );

                    const phoneInput =
                        document.getElementById(
                            "phone"
                        );

                    const addressInput =
                        document.getElementById(
                            "address"
                        );

                    const cityInput =
                        document.getElementById(
                            "city"
                        );

                    const stateInput =
                        document.getElementById(
                            "state"
                        );

                    const pincodeInput =
                        document.getElementById(
                            "pincode"
                        );


                    if (
                        !nameInput ||
                        !emailInput ||
                        !phoneInput ||
                        !addressInput ||
                        !cityInput ||
                        !stateInput ||
                        !pincodeInput
                    ) {

                        showMessage(
                            "Checkout form is incomplete."
                        );

                        return;
                    }


                    /* -------------------------------------
                       FORM VALUES
                    ------------------------------------- */

                    const customerName =
                        nameInput.value.trim();

                    const email =
                        emailInput.value.trim();

                    const phone =
                        phoneInput.value.trim();

                    const address =
                        addressInput.value.trim();

                    const city =
                        cityInput.value.trim();

                    const state =
                        stateInput.value.trim();

                    const pincode =
                        pincodeInput.value.trim();


                    /* -------------------------------------
                       PHONE VALIDATION
                    ------------------------------------- */

                    if (
                        !/^\d{10}$/.test(
                            phone
                        )
                    ) {

                        showMessage(
                            "Please enter a valid 10-digit phone number."
                        );

                        phoneInput.focus();

                        return;
                    }


                    /* -------------------------------------
                       PIN CODE VALIDATION
                    ------------------------------------- */

                    if (
                        !/^\d{6}$/.test(
                            pincode
                        )
                    ) {

                        showMessage(
                            "Please enter a valid 6-digit PIN code."
                        );

                        pincodeInput.focus();

                        return;
                    }


                    /* -------------------------------------
                       PREPARE COD ORDER DATA
                    ------------------------------------- */

                    const orderData = {

                        customer_name:
                            customerName,

                        email:
                            email,

                        phone:
                            phone,

                        address:
                            address,

                        city:
                            city,

                        state:
                            state,

                        pincode:
                            pincode,

                        items:
                            cart.map(
                                function (item) {

                                    return {

                                        id:
                                            item.id,

                                        name:
                                            item.name,

                                        quantity:
                                            Number(
                                                item.quantity
                                            )
                                    };
                                }
                            )
                    };


                    /* -------------------------------------
                       DISABLE ORDER BUTTON
                    ------------------------------------- */

                    if (
                        placeOrderButton
                    ) {

                        placeOrderButton.disabled =
                            true;


                        placeOrderButton.textContent =
                            "Placing Order...";
                    }


                    /* -------------------------------------
                       SEND ORDER TO FLASK
                    ------------------------------------- */

                    try {

                        const response =
                            await fetch(
                                "/api/orders",
                                {
                                    method:
                                        "POST",

                                    headers: {
                                        "Content-Type":
                                            "application/json"
                                    },

                                    body:
                                        JSON.stringify(
                                            orderData
                                        )
                                }
                            );


                        /* ---------------------------------
                           PARSE SERVER RESPONSE
                        --------------------------------- */

                        let result;


                        try {

                            result =
                                await response.json();

                        } catch (
                            jsonError
                        ) {

                            throw new Error(
                                "The server returned an invalid response."
                            );
                        }


                        /* ---------------------------------
                           SERVER ERROR
                        --------------------------------- */

                        if (
                            !response.ok
                        ) {

                            throw new Error(
                                result.message ||
                                "Unable to place your order."
                            );
                        }


                        /* ---------------------------------
                           VERIFY SUCCESS
                        --------------------------------- */

                        if (
                            !result.success ||
                            !result.order_number
                        ) {

                            throw new Error(
                                "Order could not be completed."
                            );
                        }


                        /* ---------------------------------
                           CLEAR SAVED CART
                        --------------------------------- */

                        localStorage.removeItem(
                            "zalivioCart"
                        );


                        cart = [];


                        /* ---------------------------------
                           SUCCESS PAGE
                        --------------------------------- */

                        window.location.href =
                            "/order-success/" +
                            encodeURIComponent(
                                result.order_number
                            );


                    } catch (error) {

                        console.error(
                            "Checkout error:",
                            error
                        );


                        showMessage(
                            error.message ||
                            "Something went wrong. Please try again."
                        );


                        /* Re-enable button */

                        if (
                            placeOrderButton
                        ) {

                            placeOrderButton.disabled =
                                false;


                            placeOrderButton.textContent = "Place Order";
                        }
                    }
                }
            );
        }


        /* =================================================
           INITIALIZE CHECKOUT
        ================================================= */

        renderCheckout();
    }
);