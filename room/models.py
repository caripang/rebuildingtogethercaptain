# Copyright 2009 Luke Stone

"""Models defining all objects in the database."""

# TODO: factor out a common Person class from Captain, Staff, Supplier, and 
# their ModelForms.

import datetime
import logging
from appengine_django.models import BaseModel
# This don't work in appengine, we use djangoforms instead.
# from django.forms import ModelForm
from django import forms  # DateField, DateTimeInput
from google.appengine.ext import db
from google.appengine.ext.db import djangoforms

SALES_TAX_RATE = 0.0925
STANDARD_KIT_COST = 250.
NRD = '04/24/2010'


def DateField(label):
    """Helper to produce data fields for forms."""
    return forms.DateField(
        label=label, required=False,  
        help_text='mm/dd/yyyy',
        widget=forms.DateTimeInput(attrs={'class':'input',
                                          'size':'10'
                                          },
                                   format='%m/%d/%Y'
                                   ))

class Captain(BaseModel):
    """A work captain."""    
    name = db.StringProperty()  # "Joe User"
    # Using the UserProperty seems to be more hassle than it's worth.
    # I was getting errors about users that didn't exist when loading sample 
    # data.
    email = db.EmailProperty()  # "joe@user.com"
    email.unique = True
    email.required = True
    phone1 = db.PhoneNumberProperty()  # In UI as "preferred phone"
    phone1.verbose_name = 'Preferred Phone'
    phone2 = db.PhoneNumberProperty()  # "backup phone"
    phone2.verbose_name = 'Backup Phone'
    tshirt_size = db.StringProperty(choices=(
            'Small',
            'Medium',
            'Large',
            'X-Large',
            '2XL',
            '3XL'))
    notes = db.TextProperty()
    last_welcome = db.DateTimeProperty()
    modified = db.DateTimeProperty(auto_now=True)
    modified_by = db.UserProperty(auto_current_user=True)

    def __unicode__(self):
        return self.name


class CaptainForm(djangoforms.ModelForm):
    class Meta:
        model = Captain
        exclude = ['modified', 'modified_by', 'last_welcome']

class CaptainContactForm(djangoforms.ModelForm):
    class Meta:
         model = Captain
         exclude = ['name', 'email', 'modified', 'modified_by', 'last_welcome']

class Site(BaseModel):
    """A work site."""
    # "10001DAL" reads: 2010, #001, Daly City
    number = db.StringProperty(required=True)  
    number.unique = True
    name = db.StringProperty()  # "Belle Haven"
    name.verbose_name = 'Recipient Name'
    street = db.StringProperty()  # Not full street address, for privacy.
    applicant = db.StringProperty()
    applicant.verbose_name = 'Applicant Contact'
    sponsors = db.StringProperty()
    difficulty = db.StringProperty()     
    postal_address = db.PostalAddressProperty()  # Full street address.
    work_start = db.DateProperty()
    work_end = db.DateProperty()
    notes = db.TextProperty()     

    def __unicode__(self):
        return 'Site #%s | %s' % (self.key().id(), self.name)

class NewSite(BaseModel):
    """A work site."""
    # "10001DAL" reads: 2010, #001, Daly City
    number = db.StringProperty(required=True)  
    number.unique = True
    name = db.StringProperty()  # "Belle Haven"
    name.verbose_name = 'Recipient Name'
    # sites entered in 2010 do not have this field set explicitly
    year = db.IntegerProperty(default=2010)  
    applicant = db.StringProperty()
    applicant.verbose_name = 'Applicant Contact'
    street_number = db.StringProperty()  # Street number like 960, see street below.
    street = db.StringProperty()  # Not full street address, for privacy.
    city_state_zip = db.StringProperty()  # like Menlo Park CA 94025
    city = db.StringProperty()
    budget = db.IntegerProperty()
    number_of_standard_kits = db.IntegerProperty(default=1)
    
    def __unicode__(self):
        """Only works if self has been saved."""
        return 'Site #%s | %s' % (self.key().id(), self.name)

    def StreetAddress(self):
        return '%s %s, %s' % (self.street_number, self.street, self.city_state_zip)

    def StandardKitCost(self):
        return STANDARD_KIT_COST * self.number_of_standard_kits

    def OrderTotal(self):
        """Only works if self has been saved."""    
        cost = self.StandardKitCost()
        if self.order_set: 
            cost += sum(order.GrandTotal() for order in self.order_set)
        return cost

    def CheckRequestTotal(self):
        """Only works if self has been saved."""    
        if self.checkrequest_set: 
            return sum(cr.amount or 0 for cr in self.checkrequest_set)
        return 0

    def BudgetRemaining(self):
        return self.budget - self.OrderTotal() - self.CheckRequestTotal()

    def VisibleOrders(self):
        for order in sorted(self.order_set, 
                            key=lambda o: o.modified, reverse=True):
            if order.state != 'new':
                yield order

class SiteForm(djangoforms.ModelForm):
    work_start = DateField('Work Start Date')
    work_end = DateField('Work End Date')
    number = forms.CharField(
        max_length=100,
        help_text = '"10001DAL" reads: 2010, #001, Daly City')
    class Meta:
         model = Site

class NewSiteForm(djangoforms.ModelForm):
    number = forms.CharField(
        max_length=100,
        help_text = '"10001DAL" reads: 2010, #001, Daly City')
    class Meta:
         model = NewSite

class CaptainSiteForm(djangoforms.ModelForm):
    work_start = DateField('Work Start Date')
    work_end = DateField('Work End Date')
    class Meta:
         model = Site
         exclude = ['number', 'name', 'street', 'applicant', 'sponsors', 
                    'postal_address']


class SiteCaptain(BaseModel):
    """Associates a site and a Captain."""
    site = db.ReferenceProperty(NewSite, required=True)
    captain = db.ReferenceProperty(Captain, required=True)
    type = db.StringProperty(choices=(
            'Construction',
            'Team',
            'Volunteer',
            ))

class SiteCaptainSiteForm(djangoforms.ModelForm):
    captain = djangoforms.ModelChoiceField(
        Captain, query=Captain.all().order('name'))
    class Meta:
        model = SiteCaptain
        exclude = ['site']


class Staff(BaseModel):
    """A RTP staff member."""
    name = db.StringProperty()
    email = db.EmailProperty()
    email.unique = True
    email.required = True
    user = db.UserProperty()
    last_welcome = db.DateTimeProperty()
    notes = db.TextProperty()
    since = db.DateProperty(auto_now_add=True)

    def __unicode__(self):
        return self.name


class StaffForm(djangoforms.ModelForm):
    since = DateField('Since')
    class Meta:
         model = Staff
         exclude = ['user', 'last_welcome']


class Supplier(BaseModel):
    """A supplier of Items."""
    # TODO: fax, contact name vs. supplier name, 
    name = db.StringProperty()
    email = db.EmailProperty()
    email.unique = True
    email.required = True
    user = db.UserProperty()
    address = db.PostalAddressProperty()
    phone1 = db.PhoneNumberProperty()
    phone2 = db.PhoneNumberProperty()
    notes = db.TextProperty()
    since = db.DateProperty(auto_now_add=True)

    def __unicode__(self):
        return self.name


class SupplierForm(djangoforms.ModelForm):
    since = DateField('Since')
    class Meta:
         model = Supplier
         exclude = ['user']



class OrderSheet(BaseModel):
    """Set of items commonly ordered together.

    Corresponds to one of the old paper forms, like the Cleaning Supplies form.
    """
    name = db.StringProperty()    
    name.unique = True
    code =  db.StringProperty()    
    code.unique = True
    code.verbose_name = 'Three-letter code like LUM for Lumber'
    instructions = db.TextProperty(default='')
    instructions.verbose_name = (
        'Instructions to Captain, appears on order form')
    logistics_instructions = db.TextProperty(default='')
    logistics_instructions.verbose_name = (
        'Instructions to Captain, appears on logistics form')
    default_supplier = db.ReferenceProperty(Supplier)
    default_supplier.verbose_name = (
        'Default Supplier, used if Item\'s supplier is not set.')
    # Choose one of the next three.
    delivery_options = db.StringProperty(choices=['Yes', 'No'], default='No')
    delivery_options.verbose_name = ('Allow Captain to select Delivery to site')
    pickup_options = db.StringProperty(choices=['Yes', 'No'], default='No')
    pickup_options.verbose_name = (
        'Allow Captain to select Pick-up from RTP warehouse')
    retrieval_options = db.StringProperty(choices=['Yes', 'No'], default='No')
    retrieval_options.verbose_name = ('Drop-off and retrieval (like debris box)'
                                      '  Note: do not set this with either'
                                      ' delivery or pick-up')

    def __unicode__(self):
      return '%s' % (self.name)

    def HasLogistics(self):
        return (self.delivery_options == 'Yes' or 
                self.pickup_options == 'Yes' or 
                self.retrieval_options == 'Yes')

class OrderSheetForm(djangoforms.ModelForm):
     class Meta:
         model = OrderSheet
         exclude = ['created']


class Item(BaseModel):
    """Represents a type of thing that may in the inventory."""
    bar_code_number = db.IntegerProperty()
    bar_code_number.unique = True    
    name = db.StringProperty(required=True)
    name.unique = True
    description = db.StringProperty()
    # 'Each' 'Box' 'Pair' etc
    measure = db.StringProperty(
        choices=('Each', 'Roll', 'Bottle', 'Box', 'Pair', 'Board', 'Bundle',
                 'Bag', 'Ton', 'Yard', 'Sheet', 'Cartridge', 'Tube', 'Tub',
                 'Sq. Yds.', 'Gallon', 'Section', 'Home', 'Box', 'Drop-off',
                 '', 'Other'))
    # Dollars.
    unit_cost = db.FloatProperty()
    appears_on_order_form = db.ReferenceProperty(OrderSheet)
    order_form_section = db.StringProperty()
    must_be_returned = db.StringProperty(choices=['Yes', 'No'], default='No')
    picture = db.BlobProperty()
    thumbnail = db.BlobProperty()
    supplier = db.ReferenceProperty(Supplier)
    supplier_part_number = db.StringProperty()
    url = db.URLProperty()
    last_editor = db.UserProperty()
    created = db.DateTimeProperty(auto_now_add=True)
    modified = db.DateTimeProperty(auto_now=True)
    
    def __unicode__(self):
        return self.description

    def VisibleSortableLabel(self, label):
        """Strips numeric prefixes used for sorting.

        Labels may have a digit prefix which is used for sorting, but
        should not be shown to users.
        """
        if not label:
            return ''
        parts = label.split()
        if len(parts) > 0 and parts[0].isdigit():
            return ' '.join(parts[1:])
        return label

    def VisibleName(self):        
        return self.VisibleSortableLabel(self.name)

    def VisibleOrderFormSection(self):        
        return self.VisibleSortableLabel(self.order_form_section)


class ItemForm(djangoforms.ModelForm):    
    class Meta:
        model = Item
        exclude = ['last_editor', 'created', 'modified', 'thumbnail']


class OrderSheetItem(BaseModel):
    """Items in a OrderSheet."""
    order_sheet = db.ReferenceProperty(OrderSheet)
    item = db.ReferenceProperty(Item)
    quantity = db.IntegerProperty()


class Order(BaseModel):
    """A Captain can make an Order for a list of Items."""
    site = db.ReferenceProperty(NewSite, required=True)
    order_sheet = db.ReferenceProperty(OrderSheet, required=True)
    sub_total = db.FloatProperty()
    sales_tax = db.FloatProperty()  # Deprecated
    grand_total = db.FloatProperty()  # Deprecated.  Use GrandTotal()
    notes = db.TextProperty()    
    state = db.StringProperty()
    created = db.DateTimeProperty(auto_now_add=True)
    created_by = db.UserProperty(auto_current_user_add=True)
    modified = db.DateTimeProperty(auto_now=True)
    modified_by = db.UserProperty(auto_current_user=True)

    def __unicode__(self):
        return ' '.join((self.site.number, self.site.name, 
                         self.order_sheet.name, 
                         '%d items' % len(list(self.orderitem_set)), 
                         '$%0.2f' % self.GrandTotal()))
    
    def CanMakeChanges(self):
        return self.state in ('new', 'Received')

    def VisibleNotes(self):
        if self.notes is None:
            return ''
        return self.notes

    def GrandTotal(self):
        if self.sub_total is None:
            return 0.
        return self.sub_total * (1. + SALES_TAX_RATE)
    
    def SalesTax(self):
        if self.sub_total is None:
            return 0.
        return self.sub_total * SALES_TAX_RATE

    def UpdateSubTotal(self):
        """Recomputes sub_total by summing the cost of items and adding tax."""
        sub_total = 0.
        order_items = OrderItem.all().filter('order = ', self)
        order_items.filter('quantity !=', 0)
        for oi in order_items:
            if oi.item.unit_cost is not None and oi.quantity is not None:
                sub_total += oi.quantity * oi.item.unit_cost 
        if self.sub_total != sub_total:
            self.sub_total = sub_total
            self.put()
            logging.info('Updated subtotal for order %d to %0.2f', 
                         self.key().id(), sub_total)


class OrderForm(djangoforms.ModelForm):
    initial = {'pickup_on': NRD}
    class Meta:
        model = Order
        exclude = ['created', 'created_by', 'modified', 'modified_by',
                   'order_sheet', 'site', 
                   'sub_total', 'sales_tax', 'grand_total', 'state',
                   'return_on'
                   ]


class CaptainOrderForm(djangoforms.ModelForm):
    pickup_on = DateField('Pickup On')
    return_on = DateField('Return On')

    class Meta:
        model = Order
        exclude = ['last_editor', 'created', 'modified', 'order_sheet', 
                   'sub_total', 'sales_tax', 'grand_total', 'state', 'captain']


class NewOrderForm(djangoforms.ModelForm):    
    site = djangoforms.ModelChoiceField(Site, widget=forms.HiddenInput)
    order_sheet = djangoforms.ModelChoiceField(
        OrderSheet, query=OrderSheet.all().order('name'))
    class Meta:
        model = Order
        fields = ['site', 'order_sheet']


class OrderItem(BaseModel):
    """The Items that are in a given Order."""
    item = db.ReferenceProperty(Item)
    order = db.ReferenceProperty(Order)
    supplier = db.ReferenceProperty(Supplier)
    quantity = db.IntegerProperty(default=0)

    def VisibleQuantity(self):
        if self.quantity:
            return self.quantity
        else:
            return ''

    def VisibleCost(self):
        if self.quantity and self.item.unit_cost:
            return '%.2f' % (self.quantity * self.item.unit_cost)
        else:
            return ''


class Delivery(BaseModel):
    """Delivery to a site (no retrieval)."""
    site = db.ReferenceProperty(NewSite, required=True)
    delivery_date = db.StringProperty()
    delivery_date.verbose_name = 'Delivery Date (Mon-Fri only)'
    contact = db.StringProperty()
    contact.verbose_name = "Contact person (who will accept delivery)"
    contact_phone = db.StringProperty()    
    notes = db.TextProperty()
    notes.verbose_name = (
        'Instructions for delivery person')
    

class DeliveryForm(djangoforms.ModelForm):
     class Meta:
         model = Delivery
         exclude = ['site']


class OrderDelivery(BaseModel):
    """Maps Order to Delivery."""
    order = db.ReferenceProperty(Order, required=True)
    delivery = db.ReferenceProperty(Delivery, required=True)


class Pickup(BaseModel):
    """Pick up from RTP warehouse."""
    site = db.ReferenceProperty(NewSite, required=True)
    pickup_date = db.StringProperty()
    pickup_date.verbose_name = 'Pickup Date (Mon-Fri only)'
    return_date = db.StringProperty()
    return_date.verbose_name = '(Optional) Return date for durable equipment'
    contact = db.StringProperty()
    contact.verbose_name = "Contact person (who will pick up)"
    contact_phone = db.StringProperty()    
    notes = db.TextProperty()
    notes.verbose_name = (
        'Instructions for warehouse staff')


class PickupForm(djangoforms.ModelForm):
     class Meta:
         model = Pickup
         exclude = ['site']


class OrderPickup(BaseModel):
    """Maps Order to Pickup."""
    order = db.ReferenceProperty(Order, required=True)
    pickup = db.ReferenceProperty(Pickup, required=True)


class Retrieval(BaseModel):
    """Delivery and retrieval to and from a site."""
    site = db.ReferenceProperty(NewSite, required=True)
    dropoff_date = db.StringProperty()
    dropoff_date.verbose_name = 'Delivery Date (Mon-Fri only)'
    retrieval_date = db.StringProperty()
    retrieval_date.verbose_name = 'Retrieval Date (Mon-Fri only)'
    contact = db.StringProperty()
    contact.verbose_name = "Contact person (who will accept delivery)"
    contact_phone = db.StringProperty()    
    notes = db.TextProperty()
    notes.verbose_name = (
        'Instructions for delivery person')


class RetrievalForm(djangoforms.ModelForm):
     class Meta:
         model = Retrieval
         exclude = ['site']


class OrderRetrieval(BaseModel):
    """Maps Order to Retrieval."""
    order = db.ReferenceProperty(Order, required=True)
    retrieval = db.ReferenceProperty(Retrieval, required=True)


class InventoryItem(BaseModel):
    """The Items that are in the inventory."""
    item = db.ReferenceProperty(Item)
    quantity = db.IntegerProperty(default=0)
    location = db.StringProperty()
    available_on = db.DateProperty()
    last_editor = db.UserProperty()
    modified = db.DateTimeProperty(auto_now=True)
    
class InventoryItemForm(djangoforms.ModelForm):
     class Meta:
         model = InventoryItem
         exclude = ['last_editor', 'modified', 'item']

class CheckRequest(BaseModel):
    """A Check Request is a request for reimbursement."""
    site = db.ReferenceProperty(NewSite)
    payment_date = db.DateProperty()
    captain = db.ReferenceProperty(Captain)
    amount = db.FloatProperty()
    amount.verbose_name = 'Check Amount ($)'
    description = db.TextProperty()
    name = db.StringProperty()
    name.verbose_name = 'Payable To'
    tax_id = db.StringProperty()
    address = db.TextProperty()
    category = db.StringProperty(choices=('Labor', 'Non-labor'))
    form_of_business = db.StringProperty(
        choices=('Corporation', 'Partnership', 'Sole Proprietor', 
                 'Don\'t Know'))
    last_editor = db.UserProperty()
    modified = db.DateTimeProperty(auto_now=True)
    
class CheckRequestForm(djangoforms.ModelForm):
    site = djangoforms.ModelChoiceField(Site, widget=forms.HiddenInput)
    captain = djangoforms.ModelChoiceField(Captain, widget=forms.HiddenInput)
    payment_date = DateField('Payment Date')
    class Meta:
        model = CheckRequest
        exclude = ['last_editor', 'modified']
