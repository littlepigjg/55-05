import sys
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent))

from ebook_manager.models import BookMeta
from ebook_manager.search import SearchEngine


def create_test_books():
    books = []

    book1 = BookMeta(
        title="Python数据分析实战",
        author="张三",
        description="本书详细介绍了Python在数据分析领域的应用，包括numpy、pandas、matplotlib等库的使用。",
        file_path="test/python_data_analysis.epub",
        file_format="epub",
        file_size=1024 * 1024 * 5,
        publish_date="2023-01-15",
        tags=["Python", "数据分析", "编程"],
        publisher="科技出版社",
        language="zh-CN",
        isbn="978-7-111-12345-6"
    )
    books.append(book1)

    book2 = BookMeta(
        title="Python编程从入门到精通",
        author="李四",
        description="Python编程语言的入门教材，适合初学者学习。从基础语法到高级应用，全面覆盖。",
        file_path="test/python_intro.pdf",
        file_format="pdf",
        file_size=1024 * 1024 * 8,
        publish_date="2022-06-20",
        tags=["Python", "入门", "编程"],
        publisher="计算机出版社",
        language="zh-CN",
        isbn="978-7-111-23456-7"
    )
    books.append(book2)

    book3 = BookMeta(
        title="机器学习实战",
        author="王五",
        description="机器学习算法的实战指南，包含大量示例代码和案例分析。使用Python实现各种机器学习算法。",
        file_path="test/ml_in_action.epub",
        file_format="epub",
        file_size=1024 * 1024 * 12,
        publish_date="2023-08-10",
        tags=["机器学习", "Python", "AI"],
        publisher="AI出版社",
        language="zh-CN",
        isbn="978-7-111-34567-8"
    )
    books.append(book3)

    book4 = BookMeta(
        title="深度学习入门",
        author="赵六",
        description="深度学习的基础理论和实践应用，包括神经网络、卷积神经网络、循环神经网络等。",
        file_path="test/deep_learning.pdf",
        file_format="pdf",
        file_size=1024 * 1024 * 15,
        publish_date="2024-03-05",
        tags=["深度学习", "神经网络", "AI"],
        publisher="科技出版社",
        language="zh-CN",
        isbn="978-7-111-45678-9"
    )
    books.append(book4)

    book5 = BookMeta(
        title="数据结构与算法",
        author="孙七",
        description="计算机科学的核心课程，详细讲解各种数据结构和算法设计。",
        file_path="test/data_structures.epub",
        file_format="epub",
        file_size=1024 * 1024 * 6,
        publish_date="2021-11-25",
        tags=["数据结构", "算法", "计算机基础"],
        publisher="计算机出版社",
        language="zh-CN",
        isbn="978-7-111-56789-0"
    )
    books.append(book5)

    return books


def test_search_engine():
    print("=" * 60)
    print("测试电子书全文搜索系统")
    print("=" * 60)

    test_dir = Path("test_index")
    if test_dir.exists():
        import shutil
        shutil.rmtree(test_dir)

    search_engine = SearchEngine(base_dir=str(test_dir))
    print("\n✅ 搜索引擎初始化成功")

    books = create_test_books()
    print(f"✅ 创建了 {len(books)} 本测试书籍")

    print("\n" + "-" * 60)
    print("开始增量索引...")
    indexed, skipped = search_engine.index_books(
        books,
        extract_content=False,
        progress_callback=lambda c, t, p: print(f"  索引中 {c}/{t}: {Path(p).name}")
    )
    print(f"✅ 索引完成: 新增/更新 {indexed} 本，跳过 {skipped} 本")

    print("\n" + "-" * 60)
    print("测试搜索功能:")

    test_cases = [
        ("python AND 数据分析 NOT 入门", "布尔逻辑搜索"),
        ("\"Python编程\"", "短语匹配搜索"),
        ("数据~", "模糊搜索"),
        ("机器学习", "普通关键词搜索"),
        ("出版社:科技出版社", "字段限定搜索"),
    ]

    for query, desc in test_cases:
        print(f"\n【{desc}】查询: {query}")
        results = search_engine.search(query, limit=10)
        print(f"  找到 {len(results)} 个结果:")
        for i, r in enumerate(results):
            print(f"    {i+1}. {r.get('title', '')} (得分: {r.get('score', 0):.2f})")
            print(f"       作者: {r.get('author', '')}")
            print(f"       格式: {r.get('file_format', '').upper()}")

    print("\n" + "-" * 60)
    print("测试多维度筛选:")

    print("\n筛选 PDF 格式:")
    results = search_engine.search("Python", filter_formats=["pdf"], limit=10)
    for r in results:
        print(f"  - {r.get('title', '')} [{r.get('file_format', '').upper()}]")

    print("\n筛选标签为 'AI':")
    results = search_engine.search("", filter_tags=["AI"], limit=10)
    for r in results:
        print(f"  - {r.get('title', '')} (标签: {r.get('tags', '')})")

    print("\n按日期范围筛选 (2023年之后):")
    results = search_engine.search(
        "",
        date_start=datetime(2023, 1, 1),
        date_end=datetime(2024, 12, 31),
        limit=10
    )
    for r in results:
        print(f"  - {r.get('title', '')} ({r.get('publish_date', '')})")

    print("\n" + "-" * 60)
    print("测试索引统计:")
    stats = search_engine.get_stats()
    print(f"  总文档数: {stats.get('total_docs', 0)}")
    print(f"  索引大小: {BookMeta.format_size(stats.get('index_size', 0))}")

    print("\n" + "-" * 60)
    print("测试建议功能:")
    suggestions = search_engine.suggest("Pyth", limit=5)
    print(f"  输入 'Pyth' 的建议: {suggestions}")

    print("\n" + "-" * 60)
    print("测试增量索引 (重复索引，应跳过所有):")
    indexed, skipped = search_engine.index_books(books, extract_content=False)
    print(f"  结果: 新增/更新 {indexed} 本，跳过 {skipped} 本")

    print("\n" + "-" * 60)
    print("测试优化索引:")
    success = search_engine.optimize()
    print(f"  优化{'成功' if success else '失败'}")

    print("\n" + "-" * 60)
    print("测试清理无效索引:")
    removed = search_engine.cleanup_orphans([b.file_path for b in books[:3]])
    print(f"  移除了 {removed} 个无效索引条目")

    search_engine.close()

    print("\n" + "=" * 60)
    print("✅ 所有测试完成！")
    print("=" * 60)

    import shutil
    shutil.rmtree(test_dir, ignore_errors=True)


if __name__ == "__main__":
    try:
        test_search_engine()
    except ImportError as e:
        print(f"\n❌ 缺少依赖: {e}")
        print("请先安装依赖: pip install whoosh jieba watchdog ebooklib")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
