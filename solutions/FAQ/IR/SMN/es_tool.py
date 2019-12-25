import sys
from elasticsearch import RequestsHttpConnection, Elasticsearch
from elasticsearch.helpers import bulk

class Search(object):

    def __init__(self, ip='127.0.0.1'):
        self.es = Elasticsearch([ip], port=9200)

    def create_index(self, index_name='chat_corspu_1', index_type='ott_date'):
        _index_mappings = {
            "mappings":{
                "properties":{
                    "query":{
                        'type':'text',
                        },
                    'answer':{
                        'type':'text',
                        }
                    }
                }
            }
        if self.es.indices.exists(index=index_name) is not True:
            res = self.es.indices.create(index=index_name, body=_index_mappings)
            print(res)

class ElasticObj(object):
    
    def __init__(self, index_name,index_type, ip ="127.0.0.1"):
        self.index_name =index_name
        self.index_type = index_type
        self.es = Elasticsearch([ip],http_auth=('elastic', 'password'),port=9200)

    def Get_Data_By_Body(self, inputs):
        doc = {"query": {"bool": {'should':[{'match':{'query':inputs}}]}}}
        
        _searched = self.es.search(index=self.index_name, body=doc)

        answer_list = []
        for hit in _searched['hits']['hits']:
            answer_list.append(hit['_source']['answer'])

        return(answer_list)

if __name__ == '__main__':

    search = Search()
    search.create_index()
    obj = ElasticObj('qa_info', 'qa_detail')
    answer_list = obj.Get_Data_By_Body(sys.argv[1])
