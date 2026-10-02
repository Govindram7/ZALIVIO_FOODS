from flask import (
    Flask,
    render_template,
    request,
    jsonify,
    redirect,
    url_for,
    session,
    flash
)

from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import or_, inspect, text

from datetime import datetime
from functools import wraps
from werkzeug.utils import secure_filename

import json
import uuid
import os


# =========================================================
# APP CONFIGURATION
# =========================================================

app = Flask(
    __name__,
    static_folder="static",
    template_folder="templates"
)

app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///zalivio.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

app.config["SECRET_KEY"] = os.environ.get(
    "SECRET_KEY",
    "zalivio-local-development-key"
)

ADMIN_PASSWORD = os.environ.get(
    "ADMIN_PASSWORD",
    "Zalivio@2026"
)

db = SQLAlchemy(app)

# =========================================================
# INVENTORY ALERT CONFIGURATION
# =========================================================

LOW_STOCK_THRESHOLD = 10


# =========================================================
# PRODUCT IMAGE UPLOAD CONFIGURATION
# =========================================================

UPLOAD_FOLDER = os.path.join(
    app.static_folder,
    "images",
    "products"
)

ALLOWED_IMAGE_EXTENSIONS = {
    "jpg",
    "jpeg",
    "png",
    "webp"
}

app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

# Maximum request size for product image uploads: 5 MB
app.config["MAX_CONTENT_LENGTH"] = 5 * 1024 * 1024

# Create the upload folder automatically if it is missing.
os.makedirs(
    UPLOAD_FOLDER,
    exist_ok=True
)


# =========================================================
# PRODUCT IMAGE HELPERS
# =========================================================

def allowed_image(filename):

    if not filename or "." not in filename:
        return False

    extension = filename.rsplit(
        ".",
        1
    )[1].lower()

    return extension in ALLOWED_IMAGE_EXTENSIONS


def save_product_image(image_file):

    if not image_file or not image_file.filename:
        return None

    if not allowed_image(image_file.filename):
        raise ValueError(
            "Only JPG, JPEG, PNG and WebP images are allowed."
        )

    safe_name = secure_filename(
        image_file.filename
    )

    extension = safe_name.rsplit(
        ".",
        1
    )[1].lower()

    unique_filename = (
        uuid.uuid4().hex
        + "."
        + extension
    )

    save_path = os.path.join(
        app.config["UPLOAD_FOLDER"],
        unique_filename
    )

    image_file.save(
        save_path
    )

    # Store the path relative to static/images/.
    # Example: products/abc123.webp
    return (
        "products/"
        + unique_filename
    )


# =========================================================
# PRODUCT MODEL
# =========================================================

class Product(db.Model):

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    name = db.Column(
        db.String(150),
        nullable=False
    )

    description = db.Column(
        db.String(300),
        nullable=False,
        default=""
    )

    price = db.Column(
        db.Float,
        nullable=False
    )

    image = db.Column(
        db.String(200),
        nullable=False
    )

    stock = db.Column(
        db.Integer,
        nullable=False,
        default=0
    )

    is_active = db.Column(
        db.Boolean,
        nullable=False,
        default=True
    )

    is_archived = db.Column(
        db.Boolean,
        nullable=False,
        default=False
    )

    created_at = db.Column(
        db.DateTime,
        nullable=False,
        default=datetime.utcnow
    )


# =========================================================
# ORDER MODEL
# =========================================================

class Order(db.Model):

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    order_number = db.Column(
        db.String(50),
        unique=True,
        nullable=False
    )

    customer_name = db.Column(
        db.String(100),
        nullable=False
    )

    email = db.Column(
        db.String(120),
        nullable=False
    )

    phone = db.Column(
        db.String(20),
        nullable=False
    )

    address = db.Column(
        db.String(250),
        nullable=False
    )

    city = db.Column(
        db.String(100),
        nullable=False
    )

    state = db.Column(
        db.String(100),
        nullable=False
    )

    pincode = db.Column(
        db.String(10),
        nullable=False
    )

    items = db.Column(
        db.Text,
        nullable=False
    )

    subtotal = db.Column(
        db.Float,
        nullable=False
    )

    delivery_charge = db.Column(
        db.Float,
        nullable=False
    )

    total = db.Column(
        db.Float,
        nullable=False
    )

    payment_method = db.Column(
        db.String(30),
        nullable=False,
        default="COD"
    )

    status = db.Column(
        db.String(30),
        nullable=False,
        default="Pending"
    )

    admin_notes = db.Column(
        db.Text,
        nullable=True
    )

    # -----------------------------------------------------
    # STEP 5D - PAYMENT FIELDS
    # -----------------------------------------------------

    payment_status = db.Column(
        db.String(30),
        nullable=False,
        default="Pending"
    )

    razorpay_order_id = db.Column(
        db.String(100),
        nullable=True
    )

    razorpay_payment_id = db.Column(
        db.String(100),
        nullable=True
    )

    razorpay_signature = db.Column(
        db.String(255),
        nullable=True
    )

    created_at = db.Column(
        db.DateTime,
        nullable=False,
        default=datetime.utcnow
    )


# =========================================================
# ADMIN PROTECTION
# =========================================================

def admin_required(function):

    @wraps(function)
    def decorated_function(*args, **kwargs):

        if not session.get("admin_logged_in"):

            return redirect(
                url_for("admin_login")
            )

        return function(
            *args,
            **kwargs
        )

    return decorated_function


# =========================================================
# HELPER - READ ORDER ITEMS
# =========================================================

def get_order_items(order):

    try:

        items = json.loads(
            order.items
        )

        if isinstance(items, list):
            return items

    except (
        json.JSONDecodeError,
        TypeError
    ):

        pass

    return []


# =========================================================
# HELPER - FIND PRODUCT FROM ORDER ITEM
# =========================================================

def find_product_from_order_item(item):

    product = None

    product_id = item.get("id")

    # -----------------------------------------------------
    # FIRST TRY PRODUCT ID
    # -----------------------------------------------------

    if product_id is not None:

        try:

            product = db.session.get(
                Product,
                int(product_id)
            )

        except (
            TypeError,
            ValueError
        ):

            product = None

    # -----------------------------------------------------
    # SUPPORT OLD ORDERS THAT DO NOT HAVE PRODUCT ID
    # -----------------------------------------------------

    if product is None:

        product_name = str(
            item.get(
                "name",
                ""
            )
        ).strip()

        if product_name:

            product = Product.query.filter_by(
                name=product_name
            ).first()

    return product


# =========================================================
# HOME
# =========================================================

@app.route("/")
def home():

    products = Product.query.filter_by(
        is_active=True,
        is_archived=False
    ).order_by(
        Product.id.asc()
    ).all()

    return render_template(
        "index.html",
        products=products
    )


# =========================================================
# CHECKOUT
# =========================================================

@app.route("/checkout")
def checkout():

    return render_template(
        "checkout.html"
    )


# =========================================================
# CREATE ORDER
# =========================================================

@app.route(
    "/api/orders",
    methods=["POST"]
)
def create_order():

    try:

        data = request.get_json(
            silent=True
        )

        if not data:

            return jsonify({
                "success": False,
                "message": "No order data received."
            }), 400

        required_fields = [
            "customer_name",
            "email",
            "phone",
            "address",
            "city",
            "state",
            "pincode",
            "items"
        ]

        for field in required_fields:

            if (
                field not in data
                or not data[field]
            ):

                return jsonify({
                    "success": False,
                    "message": f"{field} is required."
                }), 400

        if not isinstance(
            data["items"],
            list
        ):

            return jsonify({
                "success": False,
                "message": "Items must be a list."
            }), 400

        if len(data["items"]) == 0:

            return jsonify({
                "success": False,
                "message": "Your cart is empty."
            }), 400

        # -------------------------------------------------
        # COMBINE DUPLICATE PRODUCTS
        # -------------------------------------------------

        requested_products = {}

        for item in data["items"]:

            if not isinstance(
                item,
                dict
            ):

                return jsonify({
                    "success": False,
                    "message": "Invalid cart item."
                }), 400

            product = None

            product_id = item.get("id")

            if product_id is not None:

                try:

                    product = db.session.get(
                        Product,
                        int(product_id)
                    )

                except (
                    TypeError,
                    ValueError
                ):

                    product = None

            # Support old cart data
            if product is None:

                product_name = str(
                    item.get(
                        "name",
                        ""
                    )
                ).strip()

                if product_name:

                    product = Product.query.filter_by(
                        name=product_name
                    ).first()

            if product is None:

                return jsonify({
                    "success": False,
                    "message": (
                        "One of the products "
                        "no longer exists."
                    )
                }), 400

            if (
                not product.is_active
                or product.is_archived
            ):

                return jsonify({
                    "success": False,
                    "message": (
                        f"{product.name} "
                        "is currently unavailable."
                    )
                }), 400

            try:

                quantity = int(
                    item.get(
                        "quantity",
                        0
                    )
                )

            except (
                TypeError,
                ValueError
            ):

                return jsonify({
                    "success": False,
                    "message": "Invalid quantity."
                }), 400

            if quantity < 1:

                return jsonify({
                    "success": False,
                    "message": (
                        "Product quantity must "
                        "be at least 1."
                    )
                }), 400

            if product.id not in requested_products:

                requested_products[
                    product.id
                ] = {
                    "product": product,
                    "quantity": 0
                }

            requested_products[
                product.id
            ]["quantity"] += quantity

        # -------------------------------------------------
        # VALIDATE FINAL QUANTITIES
        # -------------------------------------------------

        validated_items = []

        products_to_reduce = []

        subtotal = 0

        for product_data in requested_products.values():

            product = product_data[
                "product"
            ]

            quantity = product_data[
                "quantity"
            ]

            if quantity > 20:

                return jsonify({
                    "success": False,
                    "message": (
                        f"Maximum quantity for "
                        f"{product.name} is 20."
                    )
                }), 400

            if product.stock < quantity:

                return jsonify({
                    "success": False,
                    "message": (
                        f"Only {product.stock} "
                        f"unit(s) of {product.name} "
                        "are currently available."
                    )
                }), 400

            price = float(
                product.price
            )

            item_total = (
                price * quantity
            )

            subtotal += item_total

            validated_items.append({
                "id": product.id,
                "name": product.name,
                "price": price,
                "quantity": quantity,
                "image": product.image,
                "item_total": item_total
            })

            products_to_reduce.append(
                (
                    product,
                    quantity
                )
            )

        # -------------------------------------------------
        # DELIVERY
        # -------------------------------------------------

        delivery_charge = (
            0
            if subtotal >= 499
            else 49
        )

        total = (
            subtotal
            + delivery_charge
        )

        # -------------------------------------------------
        # ORDER NUMBER
        # -------------------------------------------------

        order_number = (
            "ZAL-"
            + datetime.now().strftime(
                "%Y%m%d"
            )
            + "-"
            + uuid.uuid4().hex[
                :6
            ].upper()
        )

        # -------------------------------------------------
        # SAVE ORDER
        # -------------------------------------------------

        order = Order(
            order_number=order_number,

            customer_name=str(
                data["customer_name"]
            ).strip(),

            email=str(
                data["email"]
            ).strip(),

            phone=str(
                data["phone"]
            ).strip(),

            address=str(
                data["address"]
            ).strip(),

            city=str(
                data["city"]
            ).strip(),

            state=str(
                data["state"]
            ).strip(),

            pincode=str(
                data["pincode"]
            ).strip(),

            items=json.dumps(
                validated_items
            ),

            subtotal=subtotal,

            delivery_charge=delivery_charge,

            total=total,

            payment_method="COD",

            status="Pending"
        )

        db.session.add(
            order
        )

        # -------------------------------------------------
        # REDUCE INVENTORY
        # -------------------------------------------------

        for (
            product,
            quantity
        ) in products_to_reduce:

            product.stock -= quantity

        # Order and inventory are committed together.
        db.session.commit()

        return jsonify({
            "success": True,
            "message": (
                "Order placed successfully."
            ),
            "order_number": (
                order.order_number
            ),
            "subtotal": subtotal,
            "delivery_charge": (
                delivery_charge
            ),
            "total": total
        }), 201

    except Exception as error:

        db.session.rollback()

        print(
            "ORDER ERROR:",
            error
        )

        return jsonify({
            "success": False,
            "message": (
                "Something went wrong "
                "while creating the order."
            )
        }), 500


# =========================================================
# ORDER SUCCESS
# =========================================================

@app.route(
    "/order-success/<order_number>"
)
def order_success(order_number):

    order = Order.query.filter_by(
        order_number=order_number
    ).first_or_404()

    order_items = get_order_items(
        order
    )

    return render_template(
        "order-success.html",
        order=order,
        order_items=order_items
    )


# =========================================================
# CUSTOMER ORDER TRACKING
# =========================================================

@app.route(
    "/track-order",
    methods=["GET", "POST"]
)
def track_order():

    order = None
    order_items = []
    error = None
    success = None
    masked_phone = None
    cancellation_token = None

    if request.method == "POST":

        order_number = request.form.get(
            "order_number",
            ""
        ).strip().upper()

        raw_phone = request.form.get(
            "phone",
            ""
        ).strip()

        # Keep digits only so spaces, +91, dashes, etc. are normalized.
        phone_digits = "".join(
            character
            for character in raw_phone
            if character.isdigit()
        )

        # If an Indian country code was entered, use the final 10 digits.
        if (
            len(phone_digits) == 12
            and phone_digits.startswith("91")
        ):
            phone_digits = phone_digits[-10:]

        valid_order_number = (
            1 <= len(order_number) <= 50
            and order_number.startswith("ZAL-")
        )

        valid_phone = (
            len(phone_digits) == 10
            and phone_digits.isdigit()
        )

        if not valid_order_number or not valid_phone:

            error = (
                "We couldn't find an order "
                "with those details."
            )

        else:

            order = Order.query.filter_by(
                order_number=order_number,
                phone=phone_digits
            ).first()

            if order is None:

                error = (
                    "We couldn't find an order "
                    "with those details."
                )

            else:

                order_items = get_order_items(order)

                masked_phone = (
                    "******"
                    + phone_digits[-4:]
                )

                # Create a short-lived verification token in the signed session.
                # The customer must successfully verify order number + phone
                # before the cancellation form becomes available.
                cancellation_token = uuid.uuid4().hex

                session["customer_cancel_auth"] = {
                    "order_id": order.id,
                    "token": cancellation_token
                }

    return render_template(
        "track-order.html",
        order=order,
        order_items=order_items,
        error=error,
        success=success,
        masked_phone=masked_phone,
        cancellation_token=cancellation_token
    )


# =========================================================
# STEP 6G - CUSTOMER ORDER CANCELLATION
# =========================================================

@app.route(
    "/track-order/cancel",
    methods=["POST"]
)
def customer_cancel_order():

    order_number = request.form.get(
        "order_number",
        ""
    ).strip().upper()

    cancellation_token = request.form.get(
        "cancellation_token",
        ""
    ).strip()

    auth = session.get(
        "customer_cancel_auth"
    )

    if (
        not auth
        or not cancellation_token
        or auth.get("token") != cancellation_token
    ):
        session.pop("customer_cancel_auth", None)

        return render_template(
            "track-order.html",
            order=None,
            order_items=[],
            error=(
                "Your order verification expired. "
                "Please track the order again before cancelling."
            ),
            success=None,
            masked_phone=None,
            cancellation_token=None
        ), 403

    order = db.session.get(
        Order,
        auth.get("order_id")
    )

    if (
        order is None
        or order.order_number != order_number
    ):
        session.pop("customer_cancel_auth", None)

        return render_template(
            "track-order.html",
            order=None,
            order_items=[],
            error=(
                "We couldn't verify this order. "
                "Please track the order again."
            ),
            success=None,
            masked_phone=None,
            cancellation_token=None
        ), 404

    order_items = get_order_items(order)

    phone_digits = "".join(
        character
        for character in str(order.phone)
        if character.isdigit()
    )

    if (
        len(phone_digits) == 12
        and phone_digits.startswith("91")
    ):
        phone_digits = phone_digits[-10:]

    masked_phone = (
        "******" + phone_digits[-4:]
        if len(phone_digits) >= 4
        else "******"
    )

    # Customer cancellation is allowed only while the order is Pending.
    if order.status != "Pending":

        session.pop("customer_cancel_auth", None)

        return render_template(
            "track-order.html",
            order=order,
            order_items=order_items,
            error=(
                "This order can no longer be cancelled online "
                "because its status is "
                f"{order.status}."
            ),
            success=None,
            masked_phone=masked_phone,
            cancellation_token=None
        ), 400

    try:

        # Restore inventory for every item before changing the status.
        for item in order_items:

            product = find_product_from_order_item(
                item
            )

            if product is None:
                continue

            try:
                quantity = int(
                    item.get(
                        "quantity",
                        0
                    )
                )
            except (
                TypeError,
                ValueError
            ):
                quantity = 0

            if quantity > 0:
                product.stock += quantity

        order.status = "Cancelled"

        # Status and inventory are committed together.
        db.session.commit()

    except Exception as error:

        db.session.rollback()

        print(
            "CUSTOMER CANCELLATION ERROR:",
            error
        )

        return render_template(
            "track-order.html",
            order=order,
            order_items=order_items,
            error=(
                "We could not cancel your order right now. "
                "Please try again."
            ),
            success=None,
            masked_phone=masked_phone,
            cancellation_token=cancellation_token
        ), 500

    # Remove authorization so the same cancellation cannot be submitted twice.
    session.pop(
        "customer_cancel_auth",
        None
    )

    success = (
        "Your order has been cancelled successfully. "
        "The reserved stock has been returned to inventory."
    )

    return render_template(
        "track-order.html",
        order=order,
        order_items=order_items,
        error=None,
        success=success,
        masked_phone=masked_phone,
        cancellation_token=None
    )


# =========================================================
# ADMIN LOGIN
# =========================================================

@app.route(
    "/admin/login",
    methods=["GET", "POST"]
)
def admin_login():

    if session.get(
        "admin_logged_in"
    ):

        return redirect(
            url_for(
                "admin_orders"
            )
        )

    error = None

    if request.method == "POST":

        password = request.form.get(
            "password",
            ""
        )

        if password == ADMIN_PASSWORD:

            session[
                "admin_logged_in"
            ] = True

            return redirect(
                url_for(
                    "admin_orders"
                )
            )

        error = (
            "Incorrect password. "
            "Please try again."
        )

    return render_template(
        "admin-login.html",
        error=error
    )


# =========================================================
# ADMIN LOGOUT
# =========================================================

@app.route(
    "/admin/logout"
)
def admin_logout():

    session.pop(
        "admin_logged_in",
        None
    )

    return redirect(
        url_for(
            "admin_login"
        )
    )


# =========================================================
# ADMIN ORDERS
# =========================================================

@app.route(
    "/admin/orders"
)
@admin_required
def admin_orders():

    search_query = request.args.get(
        "q",
        ""
    ).strip()

    status_filter = request.args.get(
        "status",
        "All"
    ).strip()

    allowed_statuses = [
        "All",
        "Pending",
        "Confirmed",
        "Shipped",
        "Delivered",
        "Cancelled"
    ]

    if status_filter not in allowed_statuses:

        status_filter = "All"

    query = Order.query

    if search_query:

        search_value = (
            f"%{search_query}%"
        )

        query = query.filter(
            or_(
                Order.order_number.ilike(
                    search_value
                ),
                Order.customer_name.ilike(
                    search_value
                ),
                Order.phone.ilike(
                    search_value
                ),
                Order.email.ilike(
                    search_value
                )
            )
        )

    if status_filter != "All":

        query = query.filter(
            Order.status
            == status_filter
        )

    orders = query.order_by(
        Order.created_at.desc()
    ).all()

    order_rows = []

    for order in orders:

        order_rows.append({
            "order": order,
            "items": get_order_items(
                order
            )
        })

    return render_template(
        "admin-orders.html",

        order_rows=order_rows,

        search_query=search_query,

        status_filter=status_filter,

        total_orders=Order.query.count(),

        pending_count=(
            Order.query.filter_by(
                status="Pending"
            ).count()
        ),

        confirmed_count=(
            Order.query.filter_by(
                status="Confirmed"
            ).count()
        ),

        shipped_count=(
            Order.query.filter_by(
                status="Shipped"
            ).count()
        ),

        delivered_count=(
            Order.query.filter_by(
                status="Delivered"
            ).count()
        ),

        cancelled_count=(
            Order.query.filter_by(
                status="Cancelled"
            ).count()
        )
    )


# =========================================================
# ADMIN ORDER DETAILS
# =========================================================

@app.route(
    "/admin/orders/<int:order_id>"
)
@admin_required
def admin_order_details(order_id):

    order = db.get_or_404(
        Order,
        order_id
    )

    items = get_order_items(
        order
    )

    return render_template(
        "admin-order-details.html",
        order=order,
        items=items
    )


# =========================================================
# STEP 4E - ADMIN PRINT / INVOICE
# =========================================================

@app.route(
    "/admin/orders/<int:order_id>/invoice"
)
@admin_required
def admin_order_invoice(order_id):

    order = db.get_or_404(
        Order,
        order_id
    )

    items = get_order_items(
        order
    )

    return render_template(
        "admin-order-invoice.html",
        order=order,
        items=items
    )


# =========================================================
# STEP 4D - ADMIN ORDER NOTES
# =========================================================

@app.route(
    "/admin/orders/<int:order_id>/notes",
    methods=["POST"]
)
@admin_required
def update_order_notes(order_id):
    order = db.get_or_404(Order, order_id)
    admin_notes = request.form.get("admin_notes", "").strip()

    if len(admin_notes) > 2000:
        flash("Admin note must be 2000 characters or fewer.", "error")
        return redirect(url_for("admin_order_details", order_id=order.id))

    order.admin_notes = admin_notes if admin_notes else None

    try:
        db.session.commit()
    except Exception:
        db.session.rollback()
        flash("Could not save the admin note. Please try again.", "error")
        return redirect(url_for("admin_order_details", order_id=order.id))

    flash(
        "Admin order note saved successfully." if admin_notes
        else "Admin order note cleared successfully.",
        "success"
    )
    return redirect(url_for("admin_order_details", order_id=order.id))


# =========================================================
# UPDATE ORDER STATUS + INVENTORY
# =========================================================

@app.route(
    "/admin/orders/<int:order_id>/status",
    methods=["POST"]
)
@admin_required
def update_order_status(order_id):

    order = db.get_or_404(
        Order,
        order_id
    )

    new_status = request.form.get(
        "status",
        ""
    ).strip()

    allowed_statuses = [
        "Pending",
        "Confirmed",
        "Shipped",
        "Delivered",
        "Cancelled"
    ]

    if new_status not in allowed_statuses:

        flash(
            "Invalid order status.",
            "error"
        )

        return redirect(
            url_for(
                "admin_orders"
            )
        )

    old_status = order.status

    # -----------------------------------------------------
    # NOTHING CHANGED
    # -----------------------------------------------------

    if old_status == new_status:

        flash(
            (
                f"{order.order_number} "
                f"is already {new_status}."
            ),
            "success"
        )

        return_to = request.form.get(
            "return_to",
            ""
        )

        if return_to.startswith(
            "/admin/orders"
        ):

            return redirect(
                return_to
            )

        return redirect(
            url_for(
                "admin_orders"
            )
        )

    order_items = get_order_items(
        order
    )

    # -----------------------------------------------------
    # CANCEL ORDER -> RESTORE STOCK
    # -----------------------------------------------------

    if (
        new_status == "Cancelled"
        and old_status != "Cancelled"
    ):

        for item in order_items:

            product = (
                find_product_from_order_item(
                    item
                )
            )

            # Historical product may no longer exist.
            if product is None:

                continue

            try:

                quantity = int(
                    item.get(
                        "quantity",
                        0
                    )
                )

            except (
                TypeError,
                ValueError
            ):

                quantity = 0

            if quantity > 0:

                product.stock += quantity

    # -----------------------------------------------------
    # REOPEN CANCELLED ORDER -> RESERVE STOCK AGAIN
    # -----------------------------------------------------

    elif (
        old_status == "Cancelled"
        and new_status != "Cancelled"
    ):

        products_to_reduce = []

        # First validate everything.
        # Do not reduce anything until every product passes.

        for item in order_items:

            product = (
                find_product_from_order_item(
                    item
                )
            )

            if product is None:

                flash(
                    (
                        "This order cannot be reopened "
                        "because one of its products "
                        "no longer exists."
                    ),
                    "error"
                )

                return redirect(
                    url_for(
                        "admin_orders"
                    )
                )

            try:

                quantity = int(
                    item.get(
                        "quantity",
                        0
                    )
                )

            except (
                TypeError,
                ValueError
            ):

                quantity = 0

            if quantity <= 0:

                continue

            if product.stock < quantity:

                flash(
                    (
                        f"Cannot reopen "
                        f"{order.order_number}. "
                        f"{product.name} has only "
                        f"{product.stock} unit(s) "
                        f"available. "
                        f"{quantity} unit(s) "
                        "are required."
                    ),
                    "error"
                )

                return redirect(
                    url_for(
                        "admin_orders"
                    )
                )

            products_to_reduce.append(
                (
                    product,
                    quantity
                )
            )

        # All products have enough stock.
        for (
            product,
            quantity
        ) in products_to_reduce:

            product.stock -= quantity

    # -----------------------------------------------------
    # SAVE STATUS AND STOCK TOGETHER
    # -----------------------------------------------------

    order.status = new_status

    try:

        db.session.commit()

    except Exception as error:

        db.session.rollback()

        print(
            "STATUS UPDATE ERROR:",
            error
        )

        flash(
            (
                "The order status could not "
                "be updated."
            ),
            "error"
        )

        return redirect(
            url_for(
                "admin_orders"
            )
        )

    # -----------------------------------------------------
    # SUCCESS MESSAGE
    # -----------------------------------------------------

    if new_status == "Cancelled":

        flash(
            (
                f"{order.order_number} "
                "was cancelled. "
                "Inventory was restored."
            ),
            "success"
        )

    elif old_status == "Cancelled":

        flash(
            (
                f"{order.order_number} "
                f"was changed to {new_status}. "
                "Inventory was reserved again."
            ),
            "success"
        )

    else:

        flash(
            (
                f"{order.order_number} "
                f"updated to {new_status}."
            ),
            "success"
        )

    return_to = request.form.get(
        "return_to",
        ""
    )

    if return_to.startswith(
        "/admin/orders"
    ):

        return redirect(
            return_to
        )

    return redirect(
        url_for(
            "admin_orders"
        )
    )


# =========================================================
# ADMIN PRODUCTS
# =========================================================

@app.route(
    "/admin/products"
)
@admin_required
def admin_products():

    products = Product.query.filter_by(
        is_archived=False
    ).order_by(
        Product.id.asc()
    ).all()

    archived_products = Product.query.filter_by(
        is_archived=True
    ).order_by(
        Product.id.asc()
    ).all()

    total_products = len(
        products
    )

    total_stock = sum(
        product.stock
        for product in products
    )

    active_products = sum(
        1
        for product in products
        if product.is_active
    )

    out_of_stock_products = [
        product
        for product in products
        if product.stock <= 0
    ]

    low_stock_products = [
        product
        for product in products
        if 0 < product.stock <= LOW_STOCK_THRESHOLD
    ]

    out_of_stock = len(
        out_of_stock_products
    )

    low_stock_count = len(
        low_stock_products
    )

    return render_template(
        "admin-products.html",

        products=products,

        archived_products=archived_products,

        archived_count=len(
            archived_products
        ),

        total_products=total_products,

        total_stock=total_stock,

        active_products=active_products,

        out_of_stock=out_of_stock,

        low_stock_products=low_stock_products,

        low_stock_count=low_stock_count,

        out_of_stock_products=out_of_stock_products,

        low_stock_threshold=LOW_STOCK_THRESHOLD
    )


# =========================================================
# TOGGLE PRODUCT VISIBILITY
# =========================================================

@app.route(
    "/admin/products/<int:product_id>/toggle-visibility",
    methods=["POST"]
)
@admin_required
def toggle_product_visibility(product_id):

    product = db.get_or_404(
        Product,
        product_id
    )

    if product.is_archived:

        flash(
            "Restore this product before changing its visibility.",
            "error"
        )

        return redirect(
            url_for(
                "admin_products"
            )
        )

    product.is_active = not product.is_active

    try:

        db.session.commit()

    except Exception as error:

        db.session.rollback()

        print(
            "PRODUCT VISIBILITY ERROR:",
            error
        )

        flash(
            "Product visibility could not be updated.",
            "error"
        )

        return redirect(
            url_for(
                "admin_products"
            )
        )

    if product.is_active:

        flash(
            f"{product.name} is now visible on the store.",
            "success"
        )

    else:

        flash(
            f"{product.name} is now hidden from the store.",
            "success"
        )

    return redirect(
        url_for(
            "admin_products"
        )
    )


# =========================================================
# ARCHIVE PRODUCT
# =========================================================

@app.route(
    "/admin/products/<int:product_id>/archive",
    methods=["POST"]
)
@admin_required
def archive_product(product_id):

    product = db.get_or_404(
        Product,
        product_id
    )

    if product.is_archived:

        flash(
            f"{product.name} is already archived.",
            "error"
        )

        return redirect(
            url_for(
                "admin_products"
            )
        )

    product.is_archived = True
    product.is_active = False

    try:

        db.session.commit()

    except Exception as error:

        db.session.rollback()

        print(
            "PRODUCT ARCHIVE ERROR:",
            error
        )

        flash(
            "The product could not be archived.",
            "error"
        )

        return redirect(
            url_for(
                "admin_products"
            )
        )

    flash(
        f"{product.name} archived successfully.",
        "success"
    )

    return redirect(
        url_for(
            "admin_products"
        )
    )


# =========================================================
# RESTORE ARCHIVED PRODUCT
# =========================================================

@app.route(
    "/admin/products/<int:product_id>/restore",
    methods=["POST"]
)
@admin_required
def restore_product(product_id):

    product = db.get_or_404(
        Product,
        product_id
    )

    if not product.is_archived:

        flash(
            f"{product.name} is not archived.",
            "error"
        )

        return redirect(
            url_for(
                "admin_products"
            )
        )

    # Restored products stay hidden until the admin explicitly shows them.
    product.is_archived = False
    product.is_active = False

    try:

        db.session.commit()

    except Exception as error:

        db.session.rollback()

        print(
            "PRODUCT RESTORE ERROR:",
            error
        )

        flash(
            "The product could not be restored.",
            "error"
        )

        return redirect(
            url_for(
                "admin_products"
            )
        )

    flash(
        (
            f"{product.name} restored successfully. "
            "It is hidden until you choose Show Product."
        ),
        "success"
    )

    return redirect(
        url_for(
            "admin_products"
        )
    )


# =========================================================
# QUICK STOCK ADJUSTMENT
# =========================================================

@app.route(
    "/admin/products/<int:product_id>/adjust-stock",
    methods=["POST"]
)
@admin_required
def adjust_product_stock(product_id):

    product = db.get_or_404(
        Product,
        product_id
    )

    try:

        adjustment = int(
            request.form.get(
                "adjustment",
                "0"
            )
        )

    except (
        TypeError,
        ValueError
    ):

        flash(
            "Invalid stock adjustment.",
            "error"
        )

        return redirect(
            url_for(
                "admin_products"
            )
        )

    allowed_adjustments = {
        -10,
        -1,
        1,
        10
    }

    if adjustment not in allowed_adjustments:

        flash(
            "Invalid stock adjustment.",
            "error"
        )

        return redirect(
            url_for(
                "admin_products"
            )
        )

    old_stock = product.stock

    new_stock = max(
        0,
        old_stock + adjustment
    )

    product.stock = new_stock

    try:

        db.session.commit()

    except Exception as error:

        db.session.rollback()

        print(
            "STOCK ADJUSTMENT ERROR:",
            error
        )

        flash(
            "Product stock could not be updated.",
            "error"
        )

        return redirect(
            url_for(
                "admin_products"
            )
        )

    flash(
        (
            f"{product.name} stock updated "
            f"from {old_stock} to {new_stock}."
        ),
        "success"
    )

    return redirect(
        url_for(
            "admin_products"
        )
    )


# =========================================================
# UPDATE PRODUCT
# =========================================================

@app.route(
    "/admin/products/<int:product_id>/update",
    methods=["POST"]
)
@admin_required
def update_product(product_id):

    product = db.get_or_404(
        Product,
        product_id
    )

    name = request.form.get(
        "name",
        ""
    ).strip()

    description = request.form.get(
        "description",
        ""
    ).strip()

    image_file = request.files.get(
        "image"
    )

    try:

        price = float(
            request.form.get(
                "price",
                "0"
            )
        )

        stock = int(
            request.form.get(
                "stock",
                "0"
            )
        )

    except (
        TypeError,
        ValueError
    ):

        flash(
            "Price or stock value is invalid.",
            "error"
        )

        return redirect(
            url_for(
                "admin_products"
            )
        )

    if not name:

        flash(
            "Product name is required.",
            "error"
        )

        return redirect(
            url_for(
                "admin_products"
            )
        )

    if price < 0:

        flash(
            "Price cannot be negative.",
            "error"
        )

        return redirect(
            url_for(
                "admin_products"
            )
        )

    if stock < 0:

        flash(
            "Stock cannot be negative.",
            "error"
        )

        return redirect(
            url_for(
                "admin_products"
            )
        )

    duplicate_product = (
        Product.query.filter(
            Product.id != product.id,
            Product.name.ilike(name)
        ).first()
    )

    if duplicate_product:

        flash(
            "Another product with this name already exists.",
            "error"
        )

        return redirect(
            url_for(
                "admin_products"
            )
        )

    new_image = None

    if (
        image_file
        and image_file.filename
    ):

        if not allowed_image(
            image_file.filename
        ):

            flash(
                "Only JPG, JPEG, PNG and WebP images are allowed.",
                "error"
            )

            return redirect(
                url_for(
                    "admin_products"
                )
            )

        try:

            new_image = save_product_image(
                image_file
            )

        except ValueError as error:

            flash(
                str(error),
                "error"
            )

            return redirect(
                url_for(
                    "admin_products"
                )
            )

        except Exception as error:

            print(
                "IMAGE UPLOAD ERROR:",
                error
            )

            flash(
                "The new product image could not be uploaded.",
                "error"
            )

            return redirect(
                url_for(
                    "admin_products"
                )
            )

    product.name = name
    product.description = description
    product.price = price
    product.stock = stock

    if new_image:
        product.image = new_image

    try:

        db.session.commit()

    except Exception as error:

        db.session.rollback()

        print(
            "PRODUCT UPDATE ERROR:",
            error
        )

        flash(
            "The product could not be updated.",
            "error"
        )

        return redirect(
            url_for(
                "admin_products"
            )
        )

    flash(
        (
            f"{product.name} "
            "updated successfully."
        ),
        "success"
    )

    return redirect(
        url_for(
            "admin_products"
        )
    )


# =========================================================
# ADD PRODUCT
# =========================================================

@app.route(
    "/admin/products/add",
    methods=["POST"]
)
@admin_required
def add_product():

    name = request.form.get(
        "name",
        ""
    ).strip()

    description = request.form.get(
        "description",
        ""
    ).strip()

    image_file = request.files.get(
        "image"
    )

    try:

        price = float(
            request.form.get(
                "price",
                "0"
            )
        )

        stock = int(
            request.form.get(
                "stock",
                "0"
            )
        )

    except (
        TypeError,
        ValueError
    ):

        flash(
            "Please enter a valid price and stock.",
            "error"
        )

        return redirect(
            url_for(
                "admin_products"
            )
        )

    if (
        not name
        or price < 0
        or stock < 0
    ):

        flash(
            "Please enter valid product details.",
            "error"
        )

        return redirect(
            url_for(
                "admin_products"
            )
        )

    if (
        not image_file
        or not image_file.filename
    ):

        flash(
            "Please choose a product image.",
            "error"
        )

        return redirect(
            url_for(
                "admin_products"
            )
        )

    if not allowed_image(
        image_file.filename
    ):

        flash(
            "Only JPG, JPEG, PNG and WebP images are allowed.",
            "error"
        )

        return redirect(
            url_for(
                "admin_products"
            )
        )

    # Prevent duplicate product names before saving the image.
    existing_product = (
        Product.query.filter(
            Product.name.ilike(
                name
            )
        ).first()
    )

    if existing_product:

        flash(
            "A product with this name already exists.",
            "error"
        )

        return redirect(
            url_for(
                "admin_products"
            )
        )

    try:

        image = save_product_image(
            image_file
        )

    except ValueError as error:

        flash(
            str(error),
            "error"
        )

        return redirect(
            url_for(
                "admin_products"
            )
        )

    except Exception as error:

        print(
            "IMAGE UPLOAD ERROR:",
            error
        )

        flash(
            "The product image could not be uploaded.",
            "error"
        )

        return redirect(
            url_for(
                "admin_products"
            )
        )

    product = Product(
        name=name,
        description=description,
        price=price,
        stock=stock,
        image=image,
        is_active=True,
        is_archived=False
    )

    db.session.add(
        product
    )

    try:

        db.session.commit()

    except Exception as error:

        db.session.rollback()

        # Remove the newly uploaded file if database save fails.
        if (
            image
            and image.startswith(
                "products/"
            )
        ):

            uploaded_path = os.path.join(
                app.static_folder,
                "images",
                image
            )

            try:
                if os.path.isfile(
                    uploaded_path
                ):
                    os.remove(
                        uploaded_path
                    )
            except OSError:
                pass

        print(
            "PRODUCT ADD ERROR:",
            error
        )

        flash(
            "The product could not be added.",
            "error"
        )

        return redirect(
            url_for(
                "admin_products"
            )
        )

    flash(
        (
            f"{name} "
            "added successfully."
        ),
        "success"
    )

    return redirect(
        url_for(
            "admin_products"
        )
    )


# =========================================================
# DATABASE + INITIAL PRODUCTS
# =========================================================

with app.app_context():

    # Creates missing tables only.
    # It does NOT delete your existing orders.

    db.create_all()

    # -----------------------------------------------------
    # SAFE PRODUCT ARCHIVE COLUMN UPGRADE
    # -----------------------------------------------------
    # db.create_all() does not add columns to existing tables,
    # so add only the missing archive column without deleting data.

    product_columns = {
        column["name"]
        for column in inspect(db.engine).get_columns("product")
    }

    if "is_archived" not in product_columns:

        db.session.execute(
            text(
                "ALTER TABLE product "
                "ADD COLUMN is_archived BOOLEAN "
                "NOT NULL DEFAULT 0"
            )
        )

        db.session.commit()

    # -----------------------------------------------------
    # SAFE ADMIN ORDER NOTES COLUMN UPGRADE
    # -----------------------------------------------------

    order_columns = {
        column["name"]
        for column in inspect(db.engine).get_columns("order")
    }

    if "admin_notes" not in order_columns:
        db.session.execute(
            text(
                'ALTER TABLE "order" '
                "ADD COLUMN admin_notes TEXT"
            )
        )
        db.session.commit()

    # -----------------------------------------------------
    # STEP 5D - SAFE PAYMENT COLUMN UPGRADES
    # -----------------------------------------------------
    # Existing data is preserved. Existing COD orders receive
    # the default payment_status value of Pending.

    if "payment_status" not in order_columns:
        db.session.execute(
            text(
                'ALTER TABLE "order" '
                "ADD COLUMN payment_status "
                "VARCHAR(30) NOT NULL "
                "DEFAULT 'Pending'"
            )
        )
        db.session.commit()

    if "razorpay_order_id" not in order_columns:
        db.session.execute(
            text(
                'ALTER TABLE "order" '
                "ADD COLUMN razorpay_order_id "
                "VARCHAR(100)"
            )
        )
        db.session.commit()

    if "razorpay_payment_id" not in order_columns:
        db.session.execute(
            text(
                'ALTER TABLE "order" '
                "ADD COLUMN razorpay_payment_id "
                "VARCHAR(100)"
            )
        )
        db.session.commit()

    if "razorpay_signature" not in order_columns:
        db.session.execute(
            text(
                'ALTER TABLE "order" '
                "ADD COLUMN razorpay_signature "
                "VARCHAR(255)"
            )
        )
        db.session.commit()

    # -----------------------------------------------------
    # SEED PRODUCTS ONLY WHEN PRODUCT TABLE IS EMPTY
    # -----------------------------------------------------

    if Product.query.count() == 0:

        classic = Product(
            name=(
                "Classic Roasted Makhana"
            ),
            description=(
                "Crunchy premium makhana "
                "made for delicious everyday "
                "snacking."
            ),
            price=99,
            image=(
                "classic-makhana.jpg"
            ),
            stock=50,
            is_active=True,
            is_archived=False
        )

        peri_peri = Product(
            name=(
                "Peri Peri Makhana"
            ),
            description=(
                "Crunchy premium makhana "
                "with a bold peri peri "
                "flavour."
            ),
            price=129,
            image=(
                "peri-peri-makhana.jpg"
            ),
            stock=50,
            is_active=True,
            is_archived=False
        )

        db.session.add_all([
            classic,
            peri_peri
        ])

        db.session.commit()


# =========================================================
# START FLASK
# =========================================================

if __name__ == "__main__":

    app.run(
        debug=True
    )