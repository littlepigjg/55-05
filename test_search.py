import sys
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent))

from ebook_manager.models import BookMeta
from ebook_manager.search import (
    SearchEngine,
    SearchFilters,
    FilterBuilder,
    filter_results,
    QueryBuilder,
    build_advanced_query_string,
    extract_keywords,
)


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


def test_filters_module():
    print("\n" + "=" * 60)
    print("测试 filters 模块")
    print("=" * 60)

    filters = (
        FilterBuilder()
        .with_formats(["epub"])
        .with_tags(["Python"])
        .with_date_range(start=datetime(2022, 1, 1), end=datetime(2024, 12, 31))
        .build()
    )
    print(f"✅ FilterBuilder 创建成功: {filters.has_any() = }")

    test_docs = [
        {"file_format": "epub", "tags": "Python,数据分析", "publish_date": datetime(2023, 1, 1), "file_size": 1024},
        {"file_format": "pdf", "tags": "Python,入门", "publish_date": datetime(2022, 6, 1), "file_size": 2048},
        {"file_format": "epub", "tags": "机器学习,AI", "publish_date": datetime(2023, 8, 1), "file_size": 4096},
    ]

    results = filter_results(test_docs, filters)
    print(f"✅ filter_results: {len(results)} 条结果")

    filters2 = SearchFilters.from_dict(filters.to_dict())
    print(f"✅ SearchFilters 序列化/反序列化: {filters2.has_any() = }")

    print("\n✅ filters 模块测试通过")


def test_query_builder_module():
    print("\n" + "=" * 60)
    print("测试 query_builder 模块")
    print("=" * 60)

    keywords = extract_keywords("python AND 数据分析 NOT 入门")
    print(f"✅ extract_keywords: {keywords}")

    query_str = build_advanced_query_string(
        title="Python",
        author="张三",
        publisher="科技出版社",
    )
    print(f"✅ build_advanced_query_string: {query_str}")

    print("\n✅ query_builder 模块测试通过")


def test_search_engine():
    print("\n" + "=" * 60)
    print("测试搜索引擎核心功能")
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
    print("测试 1: 普通关键词搜索")
    results = search_engine.search("Python", limit=10)
    print(f"  找到 {len(results)} 个结果")
    for i, r in enumerate(results[:3]):
        print(f"    {i+1}. {r.get('title', '')} (得分: {r.get('score', 0):.2f})")
    assert len(results) > 0, "关键词搜索应该返回结果"
    print("  ✅ 通过")

    print("\n" + "-" * 60)
    print("测试 2: 纯格式筛选（无关键词）")
    results = search_engine.search("", filter_formats=["epub"], limit=10)
    print(f"  找到 {len(results)} 个 EPUB 格式的书")
    for i, r in enumerate(results):
        print(f"    {i+1}. {r.get('title', '')} [{r.get('file_format', '').upper()}]")
    assert len(results) == 3, f"应该有3本epub，实际{len(results)}本"
    for r in results:
        assert r.get("file_format") == "epub", f"格式应该是epub，实际是{r.get('file_format')}"
    print("  ✅ 通过")

    print("\n" + "-" * 60)
    print("测试 3: 纯标签筛选（无关键词）")
    results = search_engine.search("", filter_tags=["AI"], limit=10)
    print(f"  找到 {len(results)} 个带 AI 标签的书")
    for i, r in enumerate(results):
        print(f"    {i+1}. {r.get('title', '')} (标签: {r.get('tags', '')})")
    assert len(results) >= 2, f"应该至少有2本带AI标签的书，实际{len(results)}本"
    print("  ✅ 通过")

    print("\n" + "-" * 60)
    print("测试 4: 纯日期范围筛选（无关键词）")
    results = search_engine.search(
        "",
        date_start=datetime(2023, 1, 1),
        date_end=datetime(2024, 12, 31),
        limit=10
    )
    print(f"  找到 {len(results)} 本 2023-2024 年出版的书")
    for i, r in enumerate(results):
        print(f"    {i+1}. {r.get('title', '')} ({r.get('publish_date', '')})")
    assert len(results) >= 3, f"应该至少有3本2023年后出版的书，实际{len(results)}本"
    print("  ✅ 通过")

    print("\n" + "-" * 60)
    print("测试 5: 组合筛选（格式 + 标签，无关键词）")
    results = search_engine.search(
        "",
        filter_formats=["pdf"],
        filter_tags=["AI"],
        limit=10
    )
    print(f"  找到 {len(results)} 本 PDF 格式且带 AI 标签的书")
    for i, r in enumerate(results):
        print(f"    {i+1}. {r.get('title', '')} [{r.get('file_format', '').upper()}]")
    assert len(results) >= 1, f"应该至少有1本PDF且带AI标签的书，实际{len(results)}本"
    print("  ✅ 通过")

    print("\n" + "-" * 60)
    print("测试 6: 关键词 + 筛选")
    results = search_engine.search(
        "Python",
        filter_formats=["pdf"],
        limit=10
    )
    print(f"  找到 {len(results)} 本包含 Python 的 PDF 书")
    for i, r in enumerate(results):
        print(f"    {i+1}. {r.get('title', '')} [{r.get('file_format', '').upper()}]")
    assert len(results) >= 1, f"应该至少有1本包含Python的PDF书，实际{len(results)}本"
    for r in results:
        assert r.get("file_format") == "pdf", f"格式应该是pdf，实际是{r.get('file_format')}"
    print("  ✅ 通过")

    print("\n" + "-" * 60)
    print("测试 7: 使用 SearchFilters 对象筛选")
    filters = (
        FilterBuilder()
        .with_formats(["epub"])
        .with_tags(["编程"])
        .build()
    )
    results = search_engine.search_with_filters("", filters=filters, limit=10)
    print(f"  找到 {len(results)} 本 EPUB 格式且带 编程 标签的书")
    for i, r in enumerate(results):
        print(f"    {i+1}. {r.get('title', '')}")
    assert len(results) >= 2, f"应该至少有2本epub带编程标签的书，实际{len(results)}本"
    print("  ✅ 通过")

    print("\n" + "-" * 60)
    print("测试 8: 空查询 + 无筛选 = 空结果")
    results = search_engine.search("", limit=10)
    print(f"  找到 {len(results)} 个结果")
    assert len(results) == 0, "空查询无筛选时应该返回空列表"
    print("  ✅ 通过")

    print("\n" + "-" * 60)
    print("测试索引统计:")
    stats = search_engine.get_stats()
    print(f"  总文档数: {stats.get('total_docs', 0)}")
    print(f"  索引大小: {BookMeta.format_size(stats.get('index_size', 0))}")

    print("\n" + "-" * 60)
    print("测试增量索引（重复索引，应全部跳过）:")
    indexed, skipped = search_engine.index_books(books, extract_content=False)
    print(f"  结果: 新增/更新 {indexed} 本，跳过 {skipped} 本")
    assert skipped == len(books), f"应该全部跳过，实际跳过{skipped}本"
    print("  ✅ 通过")

    print("\n" + "-" * 60)
    print("测试优化索引:")
    success = search_engine.optimize()
    print(f"  优化{'成功' if success else '失败'}")
    assert success, "优化应该成功"
    print("  ✅ 通过")

    print("\n" + "-" * 60)
    print("测试清理无效索引:")
    removed = search_engine.cleanup_orphans([b.file_path for b in books[:3]])
    print(f"  移除了 {removed} 个无效索引条目")
    assert removed == 2, f"应该移除2个，实际移除{removed}个"
    print("  ✅ 通过")

    search_engine.close()

    print("\n" + "=" * 60)
    print("✅ 所有搜索功能测试通过！")
    print("=" * 60)

    import shutil
    shutil.rmtree(test_dir, ignore_errors=True)


def main():
    print("\n" + "=" * 60)
    print("电子书全文搜索系统 - 完整测试")
    print("=" * 60)

    try:
        test_filters_module()
        test_query_builder_module()
        test_search_engine()

        print("\n" + "🎉 所有测试全部通过！")
        print("\n功能清单:")
        print("  ✅ filters 模块 - 可复用的筛选逻辑")
        print("  ✅ query_builder 模块 - 可复用的查询构建")
        print("  ✅ 纯格式筛选（无关键词）")
        print("  ✅ 纯标签筛选（无关键词）")
        print("  ✅ 纯日期范围筛选（无关键词）")
        print("  ✅ 多条件组合筛选（无关键词）")
        print("  ✅ 关键词 + 筛选 组合")
        print("  ✅ SearchFilters 对象方式筛选")
        print("  ✅ 空查询无筛选返回空列表")
        print("  ✅ 增量索引")
        print("  ✅ 索引优化")
        print("  ✅ 索引清理")
        return 0

    except AssertionError as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return 1
    except ImportError as e:
        print(f"\n❌ 缺少依赖: {e}")
        print("请先安装依赖: pip install whoosh jieba watchdog")
        return 1
    except Exception as e:
        print(f"\n❌ 测试异常: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
