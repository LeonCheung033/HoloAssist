"""索引服务

提供文档解析、文本分块、FAISS向量索引创建和相似度搜索功能。
"""

from pathlib import Path

import faiss
import numpy as np

from holoassist.app.core.logger import get_logger
from holoassist.app.services.embedding_service import EmbeddingService

logger = get_logger(service="indexing_service")


class IndexingService:
    """索引服务类

    提供文档解析、文本分块、向量索引创建和相似度搜索功能。
    """

    def __init__(
        self,
        embedding_service: EmbeddingService | None = None,
        index_dir: str = "data/indices",
    ):
        """初始化索引服务

        Args:
            embedding_service: 嵌入服务实例，如果为None则创建新实例
            index_dir: 索引文件存储目录
        """
        self.embedding_service = embedding_service or EmbeddingService()
        self.index_dir = Path(index_dir)
        self.index_dir.mkdir(parents=True, exist_ok=True)

        logger.info(f"Initialized IndexingService with index_dir: {self.index_dir}")

    async def parse_document(self, file_path: str, file_type: str | None = None) -> str:
        """解析文档，提取文本内容

        Args:
            file_path: 文件路径
            file_type: 文件类型（pdf、docx），如果为None则根据文件扩展名自动判断

        Returns:
            str: 文档文本内容

        Raises:
            ValueError: 如果文件类型不支持
            FileNotFoundError: 如果文件不存在
            Exception: 文档解析错误
        """
        file_path_obj = Path(file_path)
        if not file_path_obj.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        # 自动判断文件类型
        if file_type is None:
            ext = file_path_obj.suffix.lower()
            if ext == ".pdf":
                file_type = "pdf"
            elif ext == ".docx":
                file_type = "docx"
            else:
                raise ValueError(f"Unsupported file type: {ext}. Supported types: pdf, docx")

        file_type = file_type.lower()

        try:
            if file_type == "pdf":
                return await self._parse_pdf(file_path)
            elif file_type == "docx":
                return await self._parse_docx(file_path)
            else:
                raise ValueError(f"Unsupported file type: {file_type}. Supported types: pdf, docx")
        except Exception as e:
            logger.error(f"Error parsing document {file_path}: {str(e)}")
            raise

    async def _parse_pdf(self, file_path: str) -> str:
        """解析PDF文档

        Args:
            file_path: PDF文件路径

        Returns:
            str: 文档文本内容
        """
        try:
            import PyPDF2

            text_parts = []
            with open(file_path, "rb") as file:
                pdf_reader = PyPDF2.PdfReader(file)
                for page_num in range(len(pdf_reader.pages)):
                    page = pdf_reader.pages[page_num]
                    text = page.extract_text()
                    if text.strip():
                        text_parts.append(text)

            return "\n\n".join(text_parts)
        except ImportError:
            logger.error("PyPDF2 not installed. Please install it: uv add PyPDF2")
            raise
        except Exception as e:
            logger.error(f"Error parsing PDF {file_path}: {str(e)}")
            raise

    async def _parse_docx(self, file_path: str) -> str:
        """解析DOCX文档

        Args:
            file_path: DOCX文件路径

        Returns:
            str: 文档文本内容
        """
        try:
            from docx import Document

            doc = Document(file_path)
            text_parts = []
            for paragraph in doc.paragraphs:
                text = paragraph.text.strip()
                if text:
                    text_parts.append(text)

            return "\n\n".join(text_parts)
        except ImportError:
            logger.error("python-docx not installed. Please install it: uv add python-docx")
            raise
        except Exception as e:
            logger.error(f"Error parsing DOCX {file_path}: {str(e)}")
            raise

    def chunk_text(
        self,
        text: str,
        chunk_size: int = 500,
        chunk_overlap: int = 50,
    ) -> list[str]:
        """将文本分割成chunks

        Args:
            text: 要分割的文本
            chunk_size: 每个chunk的字符数（默认500）
            chunk_overlap: chunk之间的重叠字符数（默认50）

        Returns:
            list[str]: 文本chunks列表
        """
        if not text.strip():
            return []

        chunks = []
        start = 0
        text_length = len(text)

        while start < text_length:
            end = start + chunk_size
            chunk = text[start:end]

            # 尝试在句号、换行符等位置截断，避免截断单词
            if end < text_length:
                # 查找最后一个句号或换行符
                last_period = chunk.rfind("。")
                last_newline = chunk.rfind("\n")
                last_period_en = chunk.rfind(".")

                # 选择最接近chunk_size的位置
                best_pos = max(last_period, last_newline, last_period_en)
                if best_pos > chunk_size * 0.5:  # 至少保留50%的内容
                    chunk = chunk[: best_pos + 1]
                    end = start + len(chunk)

            chunks.append(chunk.strip())
            start = end - chunk_overlap  # 重叠部分

        return [chunk for chunk in chunks if chunk]  # 过滤空chunks

    async def create_index(
        self,
        documents: list[str],
        index_name: str,
        dimension: int | None = None,
    ) -> str:
        """为文档创建FAISS向量索引

        Args:
            documents: 文档文本列表
            index_name: 索引名称（用于生成索引文件路径）
            dimension: 向量维度，如果为None则从第一个文档的embedding获取

        Returns:
            str: 索引文件路径

        Raises:
            ValueError: 如果documents为空
            Exception: 索引创建错误
        """
        if not documents:
            raise ValueError("documents list cannot be empty")

        logger.info(f"Creating index '{index_name}' for {len(documents)} documents")

        # 生成文档的嵌入向量
        embeddings = await self.embedding_service.generate_embeddings(documents)

        if not embeddings:
            raise ValueError("Failed to generate embeddings")

        # 确定向量维度
        if dimension is None:
            dimension = len(embeddings[0])
        else:
            # 验证所有向量的维度一致
            for i, emb in enumerate(embeddings):
                if len(emb) != dimension:
                    logger.warning(
                        f"Embedding {i} has dimension {len(emb)}, expected {dimension}. Using actual dimension."
                    )
                    dimension = len(emb)
                    break

        # 创建FAISS索引（使用L2距离的平面索引）
        index = faiss.IndexFlatL2(dimension)

        # 将嵌入向量转换为numpy数组
        embeddings_array = np.array(embeddings, dtype=np.float32)

        # 添加到索引
        index.add(embeddings_array)

        # 保存索引和文档
        index_path = self.index_dir / f"{index_name}.index"
        documents_path = self.index_dir / f"{index_name}.documents.txt"

        # 保存FAISS索引
        faiss.write_index(index, str(index_path))

        # 保存文档内容（每行一个文档）
        with open(documents_path, "w", encoding="utf-8") as f:
            for doc in documents:
                # 转义换行符，确保每行一个文档
                escaped_doc = doc.replace("\n", "\\n").replace("\r", "\\r")
                f.write(escaped_doc + "\n")

        logger.info(f"Index created: {index_path} ({index.ntotal} vectors)")

        return str(index_path)

    async def search_similar(
        self,
        query: str,
        index_name: str,
        top_k: int = 5,
    ) -> list[tuple[str, float]]:
        """在索引中搜索相似文档

        Args:
            query: 查询文本
            index_name: 索引名称
            top_k: 返回最相似的文档数量（默认5）

        Returns:
            list[tuple[str, float]]: (文档内容, 距离分数) 列表，按相似度排序
                                    距离越小表示越相似

        Raises:
            FileNotFoundError: 如果索引文件不存在
            Exception: 搜索错误
        """
        index_path = self.index_dir / f"{index_name}.index"
        documents_path = self.index_dir / f"{index_name}.documents.txt"

        if not index_path.exists():
            raise FileNotFoundError(f"Index not found: {index_path}")

        if not documents_path.exists():
            raise FileNotFoundError(f"Documents file not found: {documents_path}")

        # 加载索引
        index = faiss.read_index(str(index_path))

        # 加载文档
        documents = []
        with open(documents_path, encoding="utf-8") as f:
            for line in f:
                # 恢复换行符
                doc = line.strip().replace("\\n", "\n").replace("\\r", "\r")
                documents.append(doc)

        # 生成查询的嵌入向量
        query_embedding = await self.embedding_service.generate_embedding(query)

        # 转换为numpy数组
        query_vector = np.array([query_embedding], dtype=np.float32)

        # 搜索最相似的文档
        distances, indices = index.search(query_vector, min(top_k, index.ntotal))

        # 构建结果列表
        results = []
        for i, (distance, idx) in enumerate(zip(distances[0], indices[0])):
            if idx < len(documents):
                results.append((documents[idx], float(distance)))

        logger.info(f"Found {len(results)} similar documents for query: {query[:50]}...")

        return results

    def delete_index(self, index_name: str) -> bool:
        """删除索引文件

        Args:
            index_name: 索引名称

        Returns:
            bool: 是否成功删除
        """
        index_path = self.index_dir / f"{index_name}.index"
        documents_path = self.index_dir / f"{index_name}.documents.txt"

        deleted = False
        if index_path.exists():
            index_path.unlink()
            deleted = True
            logger.info(f"Deleted index file: {index_path}")

        if documents_path.exists():
            documents_path.unlink()
            deleted = True
            logger.info(f"Deleted documents file: {documents_path}")

        return deleted
