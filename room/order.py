"""Views and methods related to handling orders."""

import common
import models


def OrderList(request, order_sheet_id=None, state=None):
  """Request / -- show all orders."""
  user, _, _ = common.GetUser(request)
  q = models.Order.all().filter('state != ', 'new')
  order_sheet = None
  if order_sheet_id:
    order_sheet = models.OrderSheet.get_by_id(int(order_sheet_id))
    if order_sheet is not None:
      q.filter('order_sheet = ', order_sheet)
  orders = list(q)
  return common.Respond(request, 'order_list', 
                        {'orders': orders,
                         'order_sheet': order_sheet,
                         'order_export_checkbox_prefix': 
                         ORDER_EXPORT_CHECKBOX_PREFIX,
                         })

def OrderFulfill(request, order_id, order_sheet_id=None):
  """Start the fulfillment process for an order."""
  order = models.Order.get_by_id(int(order_id))
  q = models.OrderItem.all().filter('order = ', order).filter('quantity != ', 0)
  order_items = list(q)
  _SortOrderItemsWithSections(order_items)
  order_sheet = None
  list_args = []
  confirm_args = [int(order_id)]
  if order_sheet_id:
    order_sheet = models.OrderSheet.get_by_id(int(order_sheet_id))
    list_args.append(int(order_sheet_id))
    confirm_args.append(int(order_sheet_id))
  list_url = urlresolvers.reverse(OrderList, args=list_args)
  confirm_url = urlresolvers.reverse(OrderFulfillConfirm, args=confirm_args)
  return common.Respond(request, 'order_fulfill', 
                        {'order': order,
                         'order_sheet': order_sheet,
                         'order_items': order_items,
                         'back_to_list_url': list_url,
                         'confirm_url': confirm_url,
                         })

def OrderFulfillConfirm(request, order_id, order_sheet_id=None):
  order = models.Order.get_by_id(int(order_id))
  order.state = 'Being Filled'
  order.put()
  args = []
  if order_sheet_id is None:
    return http.HttpResponseRedirect(urlresolvers.reverse(OrderList))
  else:
    next_id = int(order_sheet_id)
    next_object = models.OrderSheet.get_by_id(next_id)
    if next_object is not None:
      return http.HttpResponseRedirect(urlresolvers.reverse(
          OrderList, args=[next_id]))
      
    next_object = models.NewSite.get_by_id(next_id)
    if next_object is not None:
      return http.HttpResponseRedirect(urlresolvers.reverse(
          SiteList, args=[next_id]))
  

ORDER_EXPORT_CHECKBOX_PREFIX='order_export_'
def OrderExport(request):
  """Export orders as CSV."""
  user, _, _ = common.GetUser(request)
  orders = []
  for var in request.POST:
    if var.startswith(ORDER_EXPORT_CHECKBOX_PREFIX):
      order_id = int(var[len(ORDER_EXPORT_CHECKBOX_PREFIX):])
      orders.append(models.Order.get_by_id(order_id))
  response = http.HttpResponse(mimetype='text/csv')
  response['Content-Disposition'] = (
    'attachment; filename=%s_orders.csv' % user.email())
  writer = csv.writer(response)
  for o in orders:
    writer.writerow(['Order ID',
                     'site.number',
                     'order_sheet.name',
                     'sub_total',
                     'sales_tax',
                     'grand_total',
                     'delivery_date',
                     'delivery_contact',
                     'delivery_contact_phone',
                     'delivery_location',
                     'pickup_on',
                     'number_of_days',
                     'return_on',
                     'notes',
                     'state',
                     'created',
                     'created_by',
                     'modified',
                     'modified_by',
                     ])
    writer.writerow([o.key().id(),
                     o.site.number,
                     o.order_sheet.name,
                     o.sub_total,
                     o.sales_tax,
                     o.grand_total,
                     o.delivery_date,
                     o.delivery_contact,
                     o.delivery_contact_phone,
                     o.delivery_location,
                     o.pickup_on,
                     o.number_of_days,
                     o.return_on,
                     o.notes,
                     o.state,
                     o.created,
                     o.created_by,
                     o.modified,
                     o.modified_by,
                     ])
    order_items = list(oi for oi in o.orderitem_set if oi.quantity)
    if order_items:
      order_items.sort(key=lambda x: (x.item.order_form_section, x.item.name))
      writer.writerow(['', 
                       'item.order_form_section',
                       'item.name', 
                       'item.unit_cost',
                       'item.measure',
                       'quantity', 
                       'supplier',
                       ])
    else:
      writer.writerow(['', 'No Items in this Order!!!'])
    for oi in order_items:
      writer.writerow(['', 
                       oi.item.order_form_section,
                       oi.item.name,
                       oi.item.unit_cost,
                       oi.item.measure,
                       oi.quantity,
                       oi.supplier,
                       ])
    writer.writerow([''])
  return response


def _SortOrderItemsWithSections(order_items):
  order_items.sort(key=lambda x: (x.item.order_form_section, x.item.name))
  prev_section = None
  for o in order_items:
    new_section = o.item.order_form_section or None
    if prev_section != new_section:
      o.first_in_section = True
    prev_section = new_section


def _OrderEditInternal(request, user, order):
  logging.info('Order %s', order)
  order_items = list(models.OrderItem.all().filter('order = ', order))
  _SortOrderItemsWithSections(order_items)  
  if order.state == 'new':
    what = 'Starting a new order.'
    submit_button_text = "Submit this order"
  else:
    what = 'Changing an existing order.'
    submit_button_text = 'Submit changes to this order'
  submit_button_fulfill_text = 'Submit and proceed to fulfillment (Staff only)'
  form = models.OrderForm(
    data=request.POST or None, 
    files=request.FILES or None,
    instance=order)
  # A little sketchy, but the best way to adjust HTML attributes of a field.
  form['notes'].field.widget.attrs['cols'] = 120
  form['notes'].field.widget.attrs['rows'] = max(
    5, len(form.instance.VisibleNotes().splitlines()))
  template_dict = {'form': form, 
                   'notes_field': form['notes'],
                   'delivery_fields': (form['delivery_date'],
                                       form['delivery_contact'],
                                       form['delivery_contact_phone'],
                                       form['delivery_location']),
                   'durable_fields':  (form['pickup_on'],
                                       form['number_of_days']),
                   'order': order, 
                   'order_items': order_items,
                   'created_by_user': common.GetUser(request, 
                                                     order.created_by)[0],
                   'modified_by_user': common.GetUser(request, 
                                                      order.modified_by)[0],
                   'sales_tax_pct': SALES_TAX_RATE * 100.,
                   'what_you_are_doing': what,
                   'submit_button_text': submit_button_text,
                   'submit_button_fulfill_text': submit_button_fulfill_text,
                   }
  
  if not request.POST or request.POST['submit'] == START_NEW_ORDER_SUBMIT:
    return common.Respond(request, 'order', template_dict)

  errors = form.errors
  if not errors:
    try:
      order = form.save(commit=False)
    except ValueError, err:
      errors['__all__'] = unicode(err)
  if errors:
    template_dict['errors'] = errors
    return common.Respond(request, 'order', template_dict)

  sub_total = 0.
  for arg in request.POST:
    if arg.startswith('item_'):
      _, order_item_key = arg.split('_', 1)
      order_item = models.OrderItem.get(order_item_key)
      quantity = request.POST[arg]
      if quantity.isdigit():
        quantity = int(quantity)
      else:
        quantity = 0
      order_item.quantity = quantity
      order_item.put()
      if order_item.item.unit_cost:
        sub_total += quantity * order_item.item.unit_cost

  order.sub_total = sub_total
  sales_tax = sub_total * SALES_TAX_RATE
  order.sales_tax = sales_tax
  order.grand_total = sub_total + sales_tax
  order.last_editor = user
  order.state = 'Received'
  order.put()

  if request.POST['submit'] == submit_button_fulfill_text:
    return http.HttpResponseRedirect(urlresolvers.reverse(OrderFulfill, 
                                     args=[order.key().id(),
                                           order.order_sheet.key().id()]))
  else:
    return http.HttpResponseRedirect('/room/site/list/%s/' 
                                     % order.site.key().id())
    

def OrderEdit(request, order_id):
  """Create or edit a order.  GET shows a blank form, POST processes it."""
  user, _, _ = common.GetUser(request)
  if user is None:
    return http.HttpResponseRedirect(users.CreateLoginURL(request.path))
  logging.info('OrderEdit(%s) POST(%s)', order_id, request.POST)
  order = models.Order.get_by_id(int(order_id))
  if order is None:
    logging.warning('order is none')
    return http.HttpResponseRedirect(urlresolvers.reverse(CaptainHome))
  return _OrderEditInternal(request, user, order)


def OrderNew(request, site_id=None, order_sheet_code=None):
  """Create a new order and forward to the edit screen."""
  user, _, _ = common.GetUser(request)
  if user is None:
    return http.HttpResponseRedirect(users.CreateLoginURL(request.path))
  site = models.NewSite.get_by_id(int(site_id))
  order_sheet = models.OrderSheet.all().filter(
    'code = ', order_sheet_code).get()
  order = models.Order(site=site, order_sheet=order_sheet, state='new')
  order.put()

  items = db.GqlQuery('SELECT * FROM Item WHERE appears_on_order_form = :1',
                      order.order_sheet)
  for item in items:
    order_item = models.OrderItem(order=order, item=item)
    order_item.put()
  return _OrderEditInternal(request, user, order)

