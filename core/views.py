from django.shortcuts import redirect, render, get_object_or_404
from django.core.exceptions import ObjectDoesNotExist
from django.views.generic.detail import DetailView
from core.models import Item, OrderItem, Order, Adress, Coupon, OrderDevilevered
from django.views.generic import ListView, View
from django.utils import timezone
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from core.forms import CheckkOutForm, CouponForm
from django.db.models import Q
from core.services.db_services import get_order_objects, filter_order_item_objects_by_slag, filter_order_objects, filter_order_item_objects, remove_item_from_orders, delete_item_from_order_items, get_all_objects_from_order_items, delete_order_if_order_items_empty, check_item_order_quantity, get_coupon, add_and_save_coupon_to_the_order, check_user_for_active_coupon, filtering_items_by_caegories, filtering_items_by_icontains_filter
from core.services.form_services import get_coupon_form_and_validate, get_code_from_from


def is_valid_form(values):
    valid = True
    for field in values:
        if field == '':
            valid = False
    return valid

class CheckoutView(LoginRequiredMixin, View):
    
    #TODO: add verification if adress exist in database, get rid of the mistake of dublication

    def get(self, *args, **kwargs):
        try:
            #order_queryset = Order.objects.get(user=self.request.user, ordered=False)
            order_queryset = get_order_objects(user=self.request.user, ordered=False)
            #form = CheckkOutForm()
        
            context = {
                'form': CheckkOutForm(),
                'couponform': CouponForm(),
                'order': order_queryset
            }

            shipping_address_queryset = Adress.objects.filter(
                user=self.request.user,
                adress_type='S',
                default=True
            )
            if shipping_address_queryset.exists():
                context.update({'default_shipping_address': shipping_address_queryset[0]})

            billing_address_qs = Adress.objects.filter(
                user=self.request.user,
                adress_type='B',
                default=True
            )
            if billing_address_qs.exists():
                context.update({'default_billing_address': billing_address_qs[0]})

            return render(self.request, "checkout-page.html", context=context)
        except ObjectDoesNotExist:
            messages.info(self.request, "You do not have an active order")
            return redirect("/")

    def post(self, *args, **kwargs):
        form = CheckkOutForm(self.request.POST or None)
        try:
            #order = Order.objects.get(user=self.request.user, ordered=False)
            order = get_order_objects(user=self.request.user, ordered=False)
            if form.is_valid():

                use_default_shipping = form.cleaned_data.get('use_default_shipping')
                if use_default_shipping:
                    print("Using the default shipping adress")
                    address_qs = Adress.objects.filter(
                        user=self.request.user,
                        adress_type='S',
                        default=True
                    )
                    if address_qs.exists():
                        shipping_adress = address_qs[0]
                        order.shipping_adress = shipping_adress
                        order.save()
                    else:
                        messages.info(self.request, "No default shipping adress available")
                        return redirect('core:checkout')
                else:
                    print("User is entering a new shipper address")
                    shipping_address1 = form.cleaned_data.get('shipping_address')
                    shipping_address2 = form.cleaned_data.get('shipping_address2')
                    shipping_country = form.cleaned_data.get('shipping_country')
                    shipping_zip = form.cleaned_data.get('shipping_zip')

                    if is_valid_form([shipping_address1, shipping_country, shipping_zip]):
                        shipping_adress = Adress(
                            user=self.request.user,
                            street_adress=shipping_address1,
                            apartment_adress=shipping_address2,
                            country=shipping_country,
                            zip=shipping_zip,
                            adress_type='S'
                        )
                        shipping_adress.save()

                        order.shipping_adress = shipping_adress
                        order.save()

                        set_default_shipping = form.cleaned_data.get('set_default_shipping')
                        if set_default_shipping:
                            shipping_adress.default = True
                            shipping_adress.save()
                    else:
                        messages.info(self.request, 'Please fill in the required shipping address fields')

                use_default_billing = form.cleaned_data.get('use_default_billing')
                same_billing_address = form.cleaned_data.get('same_billing_address')
                if same_billing_address:
                    billing_adress = shipping_adress
                    billing_adress.pk = None
                    billing_adress.save()
                    billing_adress.adress_type = 'B'
                    billing_adress.save()
                    order.billing_adress = billing_adress
                    order.save()

                elif use_default_billing:
                    print("Using the default billing adress")
                    address_qs = Adress.objects.filter(
                        user=self.request.user,
                        adress_type='B',
                        default=True
                    )
                    if address_qs.exists():
                        billing_adress = address_qs[0]
                        order.billing_adress = billing_adress
                        order.save()
                    else:
                        messages.info(self.request, "No default billing adress available")
                        return redirect('core:checkout')
                else:
                    print("User is entering a new billing address")
                    billing_address1 = form.cleaned_data.get('billing_address')
                    billing_address2 = form.cleaned_data.get('billing_address2')
                    billing_country = form.cleaned_data.get('billing_country')
                    billing_zip = form.cleaned_data.get('billing_zip')

                    if is_valid_form([billing_address1, billing_country, billing_zip]):
                        billing_adress = Adress(
                            user=self.request.user,
                            street_adress=billing_address1,
                            apartment_adress=billing_address2,
                            country=billing_country,
                            zip=billing_zip,
                            adress_type='B'
                        )
                        billing_adress.save()

                        order.billing_adress = billing_adress
                        order.save()

                        set_default_billing = form.cleaned_data.get('set_default_billing')
                        if set_default_billing:
                            billing_adress.default = True
                            billing_adress.save()
                    else:
                        messages.info(self.request, 'Please fill in the required billing address fields')
                        return redirect('core:checkout')
                orders = OrderItem.objects.all()
                ordered_items = []
                ordered_quantity = 0
                for order in orders:
                    ordered_items.append([order.quantity, order.item.title])
                    ordered_quantity += order.quantity
                string_filed = ''
                for i, item in enumerate(ordered_items, 1):
                    fstring = f'{i}. {item[1]} x {item[0]} \n'
                    string_filed += fstring
                items_list = string_filed.rstrip()
                OrderDevilevered.objects.create(user=self.request.user, item_title=items_list, quantity=ordered_quantity)
                orders.delete()
                order_obj = Order.objects.all()
                order_obj.delete()
                messages.info(self.request, 'The order has been send')
                return redirect('core:home')
            messages.warning(self.request, "Failed Checkout")
            return redirect('core:checkout')
        except ObjectDoesNotExist:
            messages.error(self.request, 'You do not have an active order')
            return redirect("core:order-summary")


class HomeView(ListView):
    
    model = Item
    paginate_by = 8
    template_name = 'home-page.html'
    context_object_name = 'items'

class OrderSummaryView(LoginRequiredMixin, View):

    def get(self, *args, **kwargs):
        try:
            #order_items = Order.objects.get(user=self.request.user, ordered=False)
            order_items = get_order_objects(user=self.request.user, ordered=False)
            context = {
                'objects': order_items
            }
            return render(self.request, 'order-summary.html', context=context)
        except ObjectDoesNotExist:
            messages.info(self.request, 'Your shopping cart is empty')
            return redirect("/")


class ItemDetailView(DetailView):

    model = Item
    template_name = 'product-page.html'

@login_required
def add_to_cart(request, slug):
    
    item = get_object_or_404(Item, slug=slug)
    order_item, _ = OrderItem.objects.get_or_create(
        item=item,
        user=request.user,
        ordered=False
    )
    order_queryset = Order.objects.filter(user=request.user, ordered=False)
    if order_queryset.exists():
        order = order_queryset[0]
        if order.items.filter(item__slug=item.slug).exists():
            order_item.quantity += 1
            order_item.save()
            messages.info(request, "This item quantity was updated")
            return redirect('core:order-summary')
        else:
            order.items.add(order_item)
            messages.info(request, "This item was aded tou your cart")
            return redirect('core:order-summary')
    else:
        ordered_date = timezone.now()
        order = Order.objects.create(user=request.user, ordered_date=ordered_date)
        order.items.add(order_item)
        messages.info(request, "This item was aded tou your cart")
        return redirect('core:order-summary')

@login_required
def remove_from_cart(request, slug):
    
    filtered_order_objects = filter_order_objects(user=request.user, ordered=False)

    if filtered_order_objects:
        filtered_order_items_by_slag = filter_order_item_objects_by_slag(
            user=request.user,
            slug=slug,
            order_quaryset=filtered_order_objects,
            ordered=False
        )
        if filtered_order_items_by_slag:
            remove_item_from_orders(
                user=request.user,
                slug=slug,
                ordered=False
            )
            delete_item_from_order_items(
                user=request.user,
                slug=slug,
                ordered=False
            )
            all_orders = get_all_objects_from_order_items()
            if all_orders.count() == 0:
                delete_order_if_order_items_empty(user=request.user, ordered=False)
                messages.info(request, 'You successfully delete all items from your cart')
                return redirect('core:home')
            messages.info(request, "This item was removed from your cart")
            return redirect('core:order-summary')
        else:
            messages.info(request, "This item was not in your cart")
            return redirect('core:order-summary', slug=slug)
    else:
        messages.info(request, "You do not have an active order yet")
        return redirect('core:product', slug=slug)


@login_required
def remove_single_item_from_cart(request, slug):

    filtered_order_objects = filter_order_objects(user=request.user, ordered=False)

    if filtered_order_objects:

        filtered_order_items_by_slag = filter_order_item_objects_by_slag(
            user=request.user,
            slug=slug,
            order_quaryset=filtered_order_objects,
            ordered=False
        )
        if filtered_order_items_by_slag:
            order_item = filter_order_item_objects(
                user=request.user,
                slug=slug,
                ordered=False
            )
            check_item_order_quantity(item=order_item)
            all_orders = get_all_objects_from_order_items()
            if all_orders.count() == 0:
                delete_order_if_order_items_empty(user=request.user, ordered=False)
                messages.info(request, 'You successfully delete all items from your cart')
                return redirect('core:home')
            messages.info(request, "This item quantity has been changed")
            return redirect('core:order-summary')
        else:
            messages.info(request, "This item was not in your cart")
            return redirect('core:product', slug=slug)
    else:
        messages.info(request, "You do not have an active order yet")
        return redirect('core:product', slug=slug)

class AddCouponView(View):

    def post(self, *args, **kwargs):
        form = CouponForm(self.request.POST or None)
        if form.is_valid():
            try:
                code = get_code_from_from(form)
                order = get_order_objects(user=self.request.user, ordered=False)
                if check_user_for_active_coupon(order=order):
                    messages.warning(self.request, 'You can not use one coupon two times')
                    return redirect("core:checkout")
                if get_coupon(self.request, code):
                    add_and_save_coupon_to_the_order(
                        order=order,
                        request=self.request,
                        code=code
                    )
                    messages.success(self.request, "This coupon was successfully added to your order")
                    return redirect("core:checkout")
                messages.warning(self.request, 'Coupon validation error')
                return redirect("core:checkout")
            except ObjectDoesNotExist:
                messages.info(self.request, "You do not have an active order")
                return redirect("core:checkout")

class RomanceView(View):

    def get(self, *args, **kwargs):

        romance_items = filtering_items_by_caegories(category='R')
        context = {'items': romance_items}
        return render(self.request, 'home-page.html', context=context)

class EducationReferenceView(View):

    def get(self, *args, **kwargs):

        education_reference_items = filtering_items_by_caegories(category='E')
        context = {'items': education_reference_items}
        return render(self.request, 'home-page.html', context=context)

class BusinessInvestingView(View):

    def get(self, *args, **kwargs):

        business_investing = filtering_items_by_caegories(category='B')
        context = {'items': business_investing}
        return render(self.request, 'home-page.html', context=context)


class SearchResult(ListView):

    model = Item
    template_name = 'home-page.html'
    context_object_name = 'items'

    def get_queryset(self):
        query = self.request.GET.get('q')
        items = filtering_items_by_icontains_filter(query=query)
        return items
