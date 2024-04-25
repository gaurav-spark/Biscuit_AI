import re

from langchain.llms import OpenAI
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_community.vectorstores.faiss import FAISS
from langchain_community.vectorstores.pinecone import Pinecone
from langchain.prompts import MaxMarginalRelevanceExampleSelector
from langchain.prompts import PromptTemplate, FewShotPromptTemplate
from langchain.chains import LLMChain
from langchain_core.output_parsers import StrOutputParser
from langchain.memory import ConversationBufferMemory
# from openai import OpenAI


class QueryProcessor:
    def __init__(self, user):
        self.examples = user.example_prompt
        self.llm = ChatOpenAI(model='gpt-3.5-turbo', temperature=0.0)
        self.embeddings = OpenAIEmbeddings()
        self.output_parser = StrOutputParser()
        self.memory = ConversationBufferMemory(memory_key="chat_history")
        # self.vectorstore = Pinecone.from_existing_index(index_name='testing', embedding=self.embeddings)
        # self.retriever = self.vectorstore.as_retriever(search_type="mmr", search_kwargs={"k": 8, 'fetch_k': 2})
        self.example_prompt = PromptTemplate(
            input_variables=["output"],
            template="Format: {output}",
        )
        self.example_selector = self.load_example_selector()

    def load_example_selector(self):
        return MaxMarginalRelevanceExampleSelector.from_examples(self.examples, self.embeddings, FAISS, k=1)

    # def process_query(self, query, namespace, chat_history):
    #     print("Query",query, "Namespace",namespace)
    #     vectorstore = Pinecone.from_existing_index(index_name='testing', embedding=self.embeddings, namespace=namespace)
    #     retriever = vectorstore.as_retriever(search_type="mmr", search_kwargs={"k": 8, 'fetch_k': 2})
    #     data_fetched_li = []
    #     data_fetched = retriever.get_relevant_documents(query)
    #     for i in data_fetched:
    #         data_fetched_li.append(i.page_content)
    #
    #     db_result = "".join(data_fetched_li)
    #     prompt_sel = self.construct_prompt(query).split("\n\n")[0]
    #     llm_result = self.generate_response(query, prompt_sel, db_result, chat_history)
    #     response_dict = {'response': llm_result['text'].split(":")[-1].strip()}
    #     chat_history.append({"Human:":query, "System:":response_dict['response']})
    #     print(f"Response Dict: \t {response_dict}")
    #     return response_dict
    def process_query(self, response, query, namespace, chat_history):

        print("Chat History", chat_history)

        vectorstore = Pinecone.from_existing_index(index_name='langchainindex', embedding=self.embeddings, namespace=namespace)
        retriever = vectorstore.as_retriever(search_type="mmr",
                                             search_kwargs={"k": 8, 'fetch_k': 2, "score_threshold": 0.9})

        def extract_entity(query, response):

            query_words_to_check = ["this", "that", "them", "above"]
            pattern = r'\b(?:' + '|'.join(map(re.escape, query_words_to_check)) + r')\b'

            if re.search(pattern, query, flags=re.IGNORECASE):
                if response:
                    client = OpenAI()
                    completion = client.chat.completions.create(
                        model="gpt-4",
                        messages=[
                            {"role": "system",
                             "content": "You are an intelligent chatbot. Only extract wine names from the given "
                                        "response. If there is no wine name in the response, return nothing."},
                            {"role": "user", "content": response}
                        ]
                    )
                    entity = completion.choices[0].message.content
                    return entity
                else:
                    entity = ''
                    return entity
            else:

                return ''

        entity = extract_entity(query, response)
        # print("RESPONSE", response)
        # print("ENTITY", entity)
        data_fetched_li = []
        data_fetched = retriever.get_relevant_documents(query + " " + str(entity))

        for i in data_fetched:
            data_fetched_li.append(i.page_content)

        db_result = "".join(data_fetched_li)
        prompt_sel = self.construct_prompt(query).split("\n\n")[0]
        # print("SELECTED PROMPT:",prompt_sel,"\nSELECTED CONTEXT:",db_result)
        llm_result = self.generate_response(query, prompt_sel, db_result, chat_history)

        response_dict = {'response': llm_result['text'].split(":")[-1].strip()}
        return response_dict

    def construct_prompt(self, query):
        dynamic_prompt = FewShotPromptTemplate(
            example_selector=self.example_selector,
            example_prompt=self.example_prompt,
            # prefix="I am providing you a sample of input and output. Take that as reference format for response and "
            #        "provide the answer of input\n",
            suffix="User: {user_query} ",
            input_variables=["user_query"],
        )
        dynamic_prompt_str = str(dynamic_prompt.format(user_query=query)).replace("{", "").replace("}", "")
        return dynamic_prompt_str

    def generate_response(self, query, prompt_sel, db_result, chat_history):
        context_prompt = PromptTemplate(
            input_variables=["example", "context"],
            template="""Your job is to provide the relevant response.
                        Given the example below, follow the format of example and use context to provide answer.
                        <example>
                        {example}
                        </example>

                        You are provide a context, based on which you have to generate response:
                        <context>
                        {context}
                        </context>
                        If someone greets with "hi" or "hello," always greet back.
                        If someone asks "How are you?" then respond with "I am good. I am a digital sommelier here to help you select the best drink. Can I help you select something?
                        Your answer should be short, concise, and meaningful with relevance to above only.
                        If the context is valid, the model should utilize the 
                        provided example to structure its response. The example line serves as a guideline/format 
                        for the chatbot's response, ensuring consistency and coherence in its interactions.""")

        example_selected_prompt = context_prompt.format(example=prompt_sel, context=db_result)

        final_prompt = PromptTemplate(
            template=str(example_selected_prompt) +
                     """You are provided with information about the chat with the Human, if relevant.
                     Relevant chat information:
                     {chat_history}
                     User:{input}""",
            input_variables=['chat_history', 'input'])

        llm_response_chain = LLMChain(llm=self.llm, prompt=final_prompt, memory=self.memory)
        return llm_response_chain({'input': query, "chat_history": chat_history})

    def select_workflow(self, query):
        workflow = (PromptTemplate.from_template(
            """Given the user question below, classify it as either being about `Drinks`, `Healthcare, medicines`, or `Other`.

            Do not respond with more than one word.

            <question>
            {question}
            </question>

            Classification:"""
        )
                    | self.llm
                    | self.output_parser)

        classification = workflow.invoke({"question": query})
        return classification
