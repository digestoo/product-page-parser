# ProductPageParser

Simple API to parse details from product page


## Requirement

Python3 or docker machine

## Run API

### Manual 

```bash
git clone git@github.com:digestoo/product-page-parser.git
cd product-page-parser
pip install -r requirements.txt
python api.py
```

### Docker

```bash
docker pull mdruzkowski/product-page-parser
docker run -it -p 5005:5005 mdruzkowski/product-page-parser
```

##  Details of supported endpoints

### parse

```bash
curl -XPOST -H "Content-Type: application/json"  -d '{"url":"link_to_product"}'  http://localhost:5005/parse
```

POST params:

- `url` - Product's url

