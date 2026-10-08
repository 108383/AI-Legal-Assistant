"""向量存储"""
import os

from langchain_chroma import Chroma
from langchain_core.documents import Document

from utils.config_handler import chroma_conf
from model.factory import embed_model
from langchain_text_splitters import RecursiveCharacterTextSplitter
from utils.path_tool import get_abs_path
from utils.file_handler import pdf_loader, txt_loader, listdir_with_allowed_type, get_file_md5_hex
from utils.logger_handler import logger

class VectorStoreService:
    def __init__(self):
        self.vector_store = Chroma(
            collection_name=chroma_conf["collection_name"],#表名
            embedding_function=embed_model,#嵌入模型
            persist_directory=get_abs_path(chroma_conf["persist_directory"])#路径
        )
        #分片器，将大段文本分块
        self.spliter = RecursiveCharacterTextSplitter(
            chunk_size=chroma_conf["chunk_size"],  #分块大小
            chunk_overlap=chroma_conf["chunk_overlap"],  #分块重叠
            separators=chroma_conf["separators"],  #分块分隔符
            length_function=len,  #分块长度函数
        )

    #获取向量存储的检索器
    def get_retriever(self):
        return self.vector_store.as_retriever(search_kwargs={"k": chroma_conf["k"]})

    #加载文档
    def load_document(self):
        """
        从数据文件夹内读取数据文件,转为向量存入向量库
        要计算文件的MD5做去重
        :return:
        """

        #检查文件的MD5值是否已经处理过
        def check_md5_hex(md5_for_check: str):
            if not os.path.exists(get_abs_path(chroma_conf["md5_hex_store"])):
                #创建文件
                open(get_abs_path(chroma_conf["md5_hex_store"]), "w", encoding="utf-8").close()
                return False    # md5 没处理过

            #存在,读取文件
            with open(get_abs_path(chroma_conf["md5_hex_store"]), "r", encoding="utf-8") as f:
                for line in f.readlines():
                    line = line.strip()
                    if line == md5_for_check:
                        return True    # md5 处理过

                return False            # md5 没处理过

        #保存文件的MD5值
        def save_md5_hex(md5_for_check: str):
            with open(get_abs_path(chroma_conf["md5_hex_store"]),"a",encoding="utf-8") as f:
                f.write(md5_for_check + "\n")

        #获取文件的文档
        def get_file_documents(read_path: str):
            #根据文件类型，返回文档
            if read_path.endswith("txt"):
                return txt_loader(read_path)
            if read_path.endswith("pdf"):
                return pdf_loader(read_path)

            return []

        allowed_files_path: list[str] = listdir_with_allowed_type(
            get_abs_path(chroma_conf["data_path"]),
            tuple(chroma_conf["allow_knowledge_file_type"]),
        )

        for path in allowed_files_path:
            #获取文件的MD5
            md5_hex = get_file_md5_hex(path)

            if check_md5_hex(md5_hex):
                logger.info(f"[加载知识库]{path}内容已存在知识库中，跳过")
                continue

            try:
                documents:list[Document] = get_file_documents(path)

                if not documents:
                    logger.warning(f"[加载知识库]{path}内没有有效文本内容,跳过")
                    continue

                split_document: list[Document] = self.spliter.split_documents(documents)

                if not split_document:
                    logger.warning(f"[加载知识库]{path}分片后没有有效文本内容,跳过")
                    continue

                #将内容存入向量库
                self.vector_store.add_documents(split_document)

                #记录这个已经处理好的文件的md5值,避免下次重复加载
                save_md5_hex(md5_hex)

                logger.info(f"[加载知识库]{path}内容加载成功")
            except Exception as e:
                #exc_info=True会打印出详细的错误信息,如果是False则不会打印详细的信息
                logger.error(f"[加载知识库]{path}内容加载失败: {str(e)}",exc_info=True)

if __name__ == '__main__':
    vs = VectorStoreService()

    vs.load_document()

    retriever = vs.get_retriever()

    res = retriever.invoke("如果正当防卫过度打死了人,会判多久?")
    for r in res:
        print(r.page_content)
        print("-"*20)