from klein import run, route, Klein
app = Klein()
import json
import treq

import extruct

from bs4 import BeautifulSoup
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
    product['price'] = offers.get('price',None) if not isinstance(offers.get('price',None),list) else offers['price'][0]
    product['availability'] = offers.get('availability',None)
    if product['availability'] is not None and 'schema.org' in product['availability']:
        product['availability'] = product['availability'].split('/')[3]
    product['currency'] = offers.get('priceCurrency',None)
    product['currency'] = offers.get('currency',product.get('currency',None))
    product['condition'] = offers.get('itemCondition',product.get('condition',None))
    product['condition'] = offers.get('condition',product.get('condition',None))
    return product

def fix_if_more_contexts(structure):
    if isinstance(structure,str) or isinstance(structure,int):
        return structure
    
    if isinstance(structure,dict):
        d = {}
        for key in structure:
            result = fix_if_more_contexts(structure[key])
            if ':' in key:
                new_key = key.split(':')[-1]
                d[new_key] = result
            else:
                d[key] = result
        return d
    else:
        d = []
        for key in structure:
            d.append(fix_if_more_contexts(key))
        return d

def check_if_type(structure, value):
    if isinstance(structure, list):
        for x in structure:
            if x.endswith(value):
                return True
    elif isinstance(structure, str):
        return structure.endswith(value)
    
    
def get_breadcrumb(breadcrumb_list):
    product = {}
    product['category'] = ' // '.join([x.get('name',
                                             x.get('title',
                                                 x.get('value',
                                                       x['item']['name'] if isinstance(x.get('item',None),dict)
                                                       else ''
                                                             ))) for x in breadcrumb_list])
    return product




def get_info_from_meta(text,url):
    product  = {}
    all_meta = extruct.extract(text,url, uniform=True)
    #print (all_meta['microdata'])
    opengraph = all_meta['opengraph']
    product['offers'] = []
    try:
        if len(opengraph) >=1:
            opengraph = opengraph[0]
            product['description'] = opengraph.get('og:description',None)
            product['image'] = opengraph.get('og:image',None)
            product['brand'] = opengraph.get('product:brand',None)
            product['name'] = opengraph.get('og:title',None)
            offer = {'price':opengraph.get('product:price:amount',
                            opengraph.get('og:price:amount',None)), 
                     'currency': opengraph.get('product:price:currency',
                            opengraph.get('og:price:currency',None))}
            if offer['price'] is not None:
                product['offers'].append(offer)

    except Exception as e:
        print(e)            
    microdata = all_meta['microdata']
    try:
        product_details = [x for x in microdata if check_if_type(x.get('@type',''),'Product')]
        if len(product_details) == 1:
            product_details = product_details[0]
            product['multiple_products'] = False
            product = merge_dicts(product,parse_product_schema(product_details))
            #product.update(parse_product_schema(product_details))

            if 'offers' in  product_details:
                offers = product_details['offers']
                if isinstance(offers,list):
                    for x in offers:
                        product['offers'].append(parse_offers_schema(x))
                else:
                    product['offers'].append(parse_offers_schema(offers))
        elif len(product_details)>1:
            product['multiple_products'] = True
            
    except Exception as e:
        print(e)
    
    jsonld = all_meta['json-ld']
    try:
        graphdetails = [x for x in jsonld if '@graph' in x]
        if len(graphdetails)>0:
            jsonld = graphdetails[0]['@graph']
        
        
        itemOffered = [x for x in jsonld if check_if_type(x.get('@type',''),'s:Offer')]
        
        if len(itemOffered)>0:
            jsonld = fix_if_more_contexts(jsonld)
            itemOffered = [x for x in jsonld if check_if_type(x.get('@type',''),'Offer')]
            product_details = itemOffered[0]
            if 'offers' in  product_details:
                offers = product_details['offers']
                if isinstance(offers,list):
                    for x in offers:
                        product['offers'].append(parse_offers_schema(x))
                else:
                    product['offers'].append(parse_offers_schema(offers))

        product_details = [x for x in jsonld if check_if_type(x.get('@type',''),'Product') ]
        if len(product_details) == 1:
            product_details = product_details[0]
            #product.update(parse_product_schema(product_details))
            product['multiple_products'] = False

            product = merge_dicts(product,parse_product_schema(product_details))

            if 'offers' in  product_details:
                offers = product_details['offers']
                if isinstance(offers,list):
                    for x in offers:
                        product['offers'].append(parse_offers_schema(x))
                else:
                    product['offers'].append(parse_offers_schema(offers))
        elif len(product_details)>1:
            product['multiple_products'] = True
    
    except Exception as e:
        print(e)
    
    try:
        if len(product) > 0:
            for p in [jsonld,microdata]:
                breadcrumb_details = [x for x in p if x.get('@type','').endswith('BreadcrumbList')]
                breadcrumb_list = [x for x in p if x.get('@type','').endswith('Breadcrumb')]
                if len(breadcrumb_details)>0:
                    breadcrumb_list = breadcrumb_details[0]['itemListElement']
                if len(breadcrumb_list)>0:
                    #product.update(get_breadcrumb(breadcrumb_list))
                    product = merge_dicts(product,get_breadcrumb(breadcrumb_list))
    except Exception as e:
        print(e)

    product['offers'] = [x for x in product['offers'] if x['price'] is not None]
    if len(product['offers']) == 0:
        del product['offers']
    return product





# not_price_words = ['od','zyskaj','powyżej','odbierz','from','get']

# def get_price(text):
#     import re
#     q = [x for x in re.findall(r'([A-z]*?)\s*([\d,\.]{2,})\s*(pln|zl|zł|€|eur|euro|gbp|£)', text)]
#     prices = []
#     for x in q:
#         try:
#             price = float(x[1].strip().replace(',','.'))
#         except:
#             continue
#         t = x[0].strip()
#         currency = x[2]
#         if len([p for p in not_price_words if t.endswith(p)])>0:
#             continue

#         if price == 0:
#             continue
#         index = text.find(x[1])
#         prices.append((price,currency,index))
    
#     if len(prices)>=2 and (prices[1][2]-prices[0][2])<30:
#         return {'price':min(prices[0][0],prices[1][0]), 'currency':prices[0][1]}
#     elif len(prices) > 0:
#         return {'price':prices[0][0], 'currency':prices[0][1]}
#     else:
#         return None

# def clean_html(html):
#     soup = BeautifulSoup(html,'lxml')
#     for s in soup(['script', 'style']):
#         s.decompose()
#     return (' '.join(soup.stripped_strings)).lower()


not_price_words = ['od','zyskaj','powyżej','odbierz','from','get']

def get_price(text):
    import re
    r = re.compile(r'(?P<text>.*?)((?P<price1>\d+[\.,]*\d*\s*(pln|zl|zł|€|eur|euro|gbp|£|\$))|(?P<price2>[£€$]\s*\d+[\.,]*\d*))')
    p = [m.groupdict() for m in r.finditer(text)]
    prices = []
    for x in p:
        bb = x['price2'] if x['price1'] is None else x['price1']
        try:
            pot_price = re.search(r'\d+[\.,]*\d*',bb).group(0)
            price = float(pot_price.strip().replace(',','.'))
        except:
            continue

        t = x['text'].strip()
        
        if len([p for p in not_price_words if t.endswith(p)])>0:
            continue
        currency = bb.replace(pot_price,'').strip()
        if price < 0.00001:
            continue
        index = text.find(bb)
        prices.append((price,currency,index))
    
    if len(prices)>=2 and (prices[1][2]-prices[0][2])<30:
        return {'price':min(prices[0][0],prices[1][0]), 'currency':prices[0][1]}
    elif len(prices) > 0:
        return {'price':prices[0][0], 'currency':prices[0][1]}
    else:
        return None

def clean_html(html):
    soup = BeautifulSoup(html,'lxml')
    for s in soup(['script', 'style']):
        s.decompose()
    return (' '.join(soup.stripped_strings)).lower()


def get_products_details(text,url):
    try:
        product = get_info_from_meta(text,url)
        if 'offers' not in product:
            price = get_price(clean_html(text))
            if price is not None:
                product['offers'] = [price]

        return product
    except Exception as e:
        print(e)

    return {}


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
