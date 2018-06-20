from klein import run, route, Klein
app = Klein()
import json
import treq

import extruct

from twisted.web.client import getPage
from twisted.internet import reactor, defer


def merge_dicts(current_product_info, new_dict):
    returned_info = dict(current_product_info)
    for x in new_dict:
        if  x not in current_product_info:
            returned_info[x] = new_dict[x]
        else:
            if new_dict[x] is not None:
                returned_info[x] = new_dict[x]
    return returned_info



def parse_product_schema(product_details):
    product = {}
    product['name'] = product_details.get('name',None)
    product['image'] = product_details.get('image',None)
    if product['image'] is not None and isinstance(product['image'],str):
        product['image'] = [product['image']]
    product['brand'] = product_details.get('brand',None)
    product['description'] = product_details.get('description',None)
    product['condition'] = product_details.get('itemCondition',None)
    product['manufacturer'] = product_details.get('manufacturer',None)
    product['color'] = product_details.get('color',None)
    return product

def parse_offers_schema(offers):
    product = {}
    product['price'] = offers.get('price',None)
    product['availability'] = offers.get('availability',None)
    if product['availability'] is not None and 'schema.org' in product['availability']:
        product['availability'] = product['availability'].split('/')[3]
    product['currency'] = offers.get('priceCurrency',None)
    product['currency'] = offers.get('currency',product.get('currency',None))
    product['condition'] = offers.get('itemCondition',product.get('condition',None))
    product['condition'] = offers.get('condition',product.get('condition',None))
    return product


def get_breadcrumb(breadcrumb_list):
    product = {}
    product['category'] = ' // '.join([x.get('name',
                                             x.get('title',
                                                 x.get('value',
                                                       x['item']['name'] if isinstance(x.get('item',None),dict)
                                                       else ''
                                                             ))) for x in breadcrumb_list])
    return product


def get_products_details(text,url):
    all_meta = extruct.extract(text,url, uniform=True)
    product = {}
    opengraph = all_meta['opengraph']
    
    if len(opengraph) == 1:
        opengraph = opengraph[0]
        product['description'] = opengraph.get('og:description',None)
        product['image'] = opengraph.get('og:image',None)
        product['brand'] = opengraph.get('product:brand',None)
        product['offers'] = []
        offer = {'price':opengraph.get('product:price:amount',None), 
                 'currency': opengraph.get('product:price:currency',None)}
        product['offers'].append(offer)
                
    microdata = all_meta['microdata']
    product_details = [x for x in microdata if x.get('@type','').endswith('Product')]
    if len(product_details) == 1:
        product_details = product_details[0]

        product = merge_dicts(product,parse_product_schema(product_details))
        #product.update(parse_product_schema(product_details))

        
        offers = [x for x in product_details if isinstance(product_details[x],dict) 
                  and product_details[x].get('@type','').endswith('Offer')]
        product['offers'] = []
        for x in offers:
            product['offers'].append(parse_offers_schema(product_details[x]))

    
    jsonld = all_meta['json-ld']
    graphdetails = [x for x in jsonld if '@graph' in x]
    if len(graphdetails)>0:
        jsonld = graphdetails[0]['@graph']
    product_details = [x for x in jsonld if x.get('@type','').endswith('Product')]
    if len(product_details) == 1:
        product_details = product_details[0]
        #product.update(parse_product_schema(product_details))
        
        product = merge_dicts(product,parse_product_schema(product_details))
        
        if 'offers' in  product_details:
            offers = product_details['offers']
            product['offers'] = []
            if isinstance(offers,list):
                for x in offers:
                    product['offers'].append(parse_offers_schema(x))
            else:
                product['offers'].append(parse_offers_schema(offers))
    
    if len(product) > 0:
        for p in [jsonld,microdata]:
            breadcrumb_details = [x for x in p if x.get('@type','').endswith('BreadcrumbList')]
            breadcrumb_list = [x for x in p if x.get('@type','').endswith('Breadcrumb')]
            if len(breadcrumb_details)>0:
                breadcrumb_list = breadcrumb_details[0]['itemListElement']
            if len(breadcrumb_list)>0:
                #product.update(get_breadcrumb(breadcrumb_list))
                product = merge_dicts(product,get_breadcrumb(breadcrumb_list))
    return product

@defer.inlineCallbacks
def return_info(response):
    text = yield response.content()
    url = response.request.absoluteURI.decode("utf-8")
    v = get_products_details(text, url)#response.request.absoluteURI)
    return json.dumps(v)


@app.route("/parse", methods=['POST'])
def get_category(request):
    content = json.loads(request.content.read())
    url = content['url']
    d = treq.get(url)
    d.addCallback(return_info)
    return d


resource = app.resource

app.run("0.0.0.0", 5005)
