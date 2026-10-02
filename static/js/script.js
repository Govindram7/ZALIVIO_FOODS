"use strict";

/* =========================================================
   ZALIVIO FOODS - MAIN WEBSITE + SHOPPING CART
========================================================= */


/* =========================================================
   LOAD CART
========================================================= */

let cart = [];

try {

    const savedCart =
        localStorage.getItem("zalivioCart");

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
   SAVE CART
========================================================= */

function saveCart() {

    try {

        localStorage.setItem(
            "zalivioCart",
            JSON.stringify(cart)
        );

    } catch (error) {

        console.error(
            "Unable to save cart:",
            error
        );
    }
}


/* =========================================================
   ADD PRODUCT TO CART
========================================================= */

function addToCart(id, name, price, image) {

    const numericId = Number(id);

    const existingItem = cart.find(
        item =>
            Number(item.id) === numericId ||
            (
                !item.id &&
                item.name === name
            )
    );

    if (existingItem) {

        if (
            Number(existingItem.quantity) >= 20
        ) {

            alert(
                "Maximum quantity is 20."
            );

            return;
        }

        existingItem.id = numericId;

        existingItem.name = name;

        existingItem.price = Number(price);

        existingItem.image = image;

        existingItem.quantity =
            Number(existingItem.quantity) + 1;

    } else {

        cart.push({
            id: numericId,
            name: name,
            price: Number(price),
            image: image,
            quantity: 1
        });
    }

    saveCart();

    renderCart();

    openCart();
}

/* =========================================================
   OPEN CART
========================================================= */

function openCart() {

    const drawer =
        document.getElementById(
            "cart-drawer"
        );

    const overlay =
        document.getElementById(
            "cart-overlay"
        );


    if (drawer) {
        drawer.classList.add("active");
    }


    if (overlay) {
        overlay.classList.add("active");
    }


    document.body.style.overflow =
        "hidden";
}


/* =========================================================
   CLOSE CART
========================================================= */

function closeCart() {

    const drawer =
        document.getElementById(
            "cart-drawer"
        );

    const overlay =
        document.getElementById(
            "cart-overlay"
        );


    if (drawer) {
        drawer.classList.remove("active");
    }


    if (overlay) {
        overlay.classList.remove("active");
    }


    document.body.style.overflow =
        "";
}


/* =========================================================
   CONTINUE SHOPPING
========================================================= */

function continueShopping() {

    closeCart();


    const products =
        document.getElementById(
            "products"
        );


    if (products) {

        products.scrollIntoView({
            behavior: "smooth",
            block: "start"
        });
    }
}


/* =========================================================
   CHANGE QUANTITY
========================================================= */

function changeQuantity(index, amount) {

    if (!cart[index]) {
        return;
    }


    const currentQuantity =
        Number(cart[index].quantity) || 1;


    cart[index].quantity =
        currentQuantity + Number(amount);


    if (cart[index].quantity <= 0) {

        cart.splice(
            index,
            1
        );
    }


    saveCart();

    renderCart();
}


/* =========================================================
   REMOVE PRODUCT
========================================================= */

function removeItem(index) {

    if (!cart[index]) {
        return;
    }


    cart.splice(
        index,
        1
    );


    saveCart();

    renderCart();
}


/* =========================================================
   FORMAT PRICE
========================================================= */

function formatPrice(amount) {

    return "₹" +
        Number(amount).toFixed(0);
}


/* =========================================================
   RENDER CART
========================================================= */

function renderCart() {

    const cartItems =
        document.getElementById(
            "cart-items"
        );

    const emptyCart =
        document.getElementById(
            "empty-cart"
        );

    const cartSummary =
        document.getElementById(
            "cart-summary"
        );

    const cartCount =
        document.getElementById(
            "cart-count"
        );


    /*
       Update navbar count even if
       cart drawer HTML is unavailable.
    */

    const totalQuantity =
        cart.reduce(
            function (total, item) {

                return total +
                    (
                        Number(
                            item.quantity
                        ) || 0
                    );
            },
            0
        );


    if (cartCount) {

        cartCount.textContent =
            totalQuantity;
    }


    if (
        !cartItems ||
        !emptyCart ||
        !cartSummary
    ) {
        return;
    }


    cartItems.innerHTML = "";


    /* -----------------------------------------------------
       EMPTY CART
    ----------------------------------------------------- */

    if (cart.length === 0) {

        cartItems.style.display =
            "none";

        emptyCart.classList.add(
            "active"
        );

        cartSummary.style.display =
            "none";

        return;
    }


    /* -----------------------------------------------------
       CART HAS PRODUCTS
    ----------------------------------------------------- */

    cartItems.style.display =
        "block";

    emptyCart.classList.remove(
        "active"
    );

    cartSummary.style.display =
        "block";


    /* -----------------------------------------------------
       CREATE CART ITEMS
    ----------------------------------------------------- */

    cart.forEach(
        function (item, index) {

            const price =
                Number(item.price) || 0;

            const quantity =
                Number(item.quantity) || 1;


            const cartItem =
                document.createElement(
                    "div"
                );


            cartItem.className =
                "cart-item";


            const imagePath =
                "/static/images/" +
                encodeURIComponent(
                    item.image || ""
                );


            cartItem.innerHTML = `

                <div class="cart-item-image">

                    <img
                        src="${imagePath}"
                        alt=""
                    >

                </div>


                <div class="cart-item-details">

                    <h4></h4>

                    <div class="cart-item-price">
                        ${formatPrice(price)}
                    </div>


                    <div class="cart-controls">

                        <div class="quantity-control">

                            <button
                                type="button"
                                class="quantity-minus"
                                aria-label="Decrease quantity"
                            >
                                −
                            </button>


                            <span>
                                ${quantity}
                            </span>


                            <button
                                type="button"
                                class="quantity-plus"
                                aria-label="Increase quantity"
                            >
                                +
                            </button>

                        </div>


                        <button
                            type="button"
                            class="remove-item"
                        >
                            Remove
                        </button>

                    </div>

                </div>
            `;


            const heading =
                cartItem.querySelector("h4");

            if (heading) {
                heading.textContent =
                    item.name;
            }


            const image =
                cartItem.querySelector("img");

            if (image) {
                image.alt =
                    item.name;
            }


            const minusButton =
                cartItem.querySelector(
                    ".quantity-minus"
                );

            const plusButton =
                cartItem.querySelector(
                    ".quantity-plus"
                );

            const removeButton =
                cartItem.querySelector(
                    ".remove-item"
                );


            if (minusButton) {

                minusButton.addEventListener(
                    "click",
                    function () {

                        changeQuantity(
                            index,
                            -1
                        );
                    }
                );
            }


            if (plusButton) {

                plusButton.addEventListener(
                    "click",
                    function () {

                        changeQuantity(
                            index,
                            1
                        );
                    }
                );
            }


            if (removeButton) {

                removeButton.addEventListener(
                    "click",
                    function () {

                        removeItem(
                            index
                        );
                    }
                );
            }


            cartItems.appendChild(
                cartItem
            );
        }
    );


    updateTotals();
}


/* =========================================================
   UPDATE TOTALS
========================================================= */

function updateTotals() {

    const subtotalElement =
        document.getElementById(
            "cart-subtotal"
        );

    const deliveryElement =
        document.getElementById(
            "delivery-charge"
        );

    const totalElement =
        document.getElementById(
            "cart-total"
        );


    if (
        !subtotalElement ||
        !deliveryElement ||
        !totalElement
    ) {
        return;
    }


    const subtotal =
        cart.reduce(
            function (total, item) {

                const price =
                    Number(item.price) || 0;

                const quantity =
                    Number(item.quantity) || 0;


                return total +
                    (
                        price *
                        quantity
                    );
            },
            0
        );


    /*
       Delivery:
       ₹49 below ₹499.
       Free at ₹499 or above.
    */

    const delivery =
        subtotal > 0 &&
        subtotal < 499
            ? 49
            : 0;


    const finalTotal =
        subtotal + delivery;


    subtotalElement.textContent =
        formatPrice(subtotal);


    deliveryElement.textContent =
        delivery === 0
            ? "FREE"
            : formatPrice(delivery);


    totalElement.textContent =
        formatPrice(finalTotal);
}


/* =========================================================
   PROCEED TO CHECKOUT
========================================================= */

function checkout() {

    if (!Array.isArray(cart) || cart.length === 0) {
        alert("Your cart is empty.");
        return;
    }

    saveCart();

    closeCart();

    window.location.href = "/checkout";
}


 


/* =========================================================
   CONTACT FORM
========================================================= */

function initializeContactForm() {

    const contactForm =
        document.getElementById(
            "contact-form"
        );


    if (!contactForm) {
        return;
    }


    contactForm.addEventListener(
        "submit",
        function (event) {

            event.preventDefault();


            alert(
                "Thank you! Your message has been received."
            );


            contactForm.reset();
        }
    );
}


/* =========================================================
   ESCAPE KEY CLOSES CART
========================================================= */

document.addEventListener(
    "keydown",
    function (event) {

        if (event.key === "Escape") {

            closeCart();
        }
    }
);


/* =========================================================
   INITIALIZE WEBSITE
========================================================= */

document.addEventListener(
    "DOMContentLoaded",
    function () {

        renderCart();

        initializeContactForm();
    }
);