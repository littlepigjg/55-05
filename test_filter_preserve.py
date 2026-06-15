import sys
import os
import importlib.util
from pathlib import Path
from datetime import date, datetime

sys.path.insert(0, str(Path(__file__).parent))

module_path = Path(__file__).parent / "ebook_manager" / "search" / "filter_assembler.py"
spec = importlib.util.spec_from_file_location("filter_assembler", module_path)
filter_assembler = importlib.util.module_from_spec(spec)
spec.loader.exec_module(filter_assembler)

SelectedItemsTracker = filter_assembler.SelectedItemsTracker
FilterAssembler = filter_assembler.FilterAssembler
AdvancedSearchCriteria = filter_assembler.AdvancedSearchCriteria
convert_mb_to_bytes = filter_assembler.convert_mb_to_bytes
convert_bytes_to_mb = filter_assembler.convert_bytes_to_mb
format_file_size = filter_assembler.format_file_size


class MockListItem:
    def __init__(self, data, selected=False):
        self._data = data
        self._selected = selected

    def data(self, role):
        return self._data

    def isSelected(self):
        return self._selected

    def setSelected(self, value):
        self._selected = value


class MockListWidget:
    def __init__(self, items_data=None):
        self._items = []
        if items_data:
            for data, selected in items_data:
                self._items.append(MockListItem(data, selected))

    def count(self):
        return len(self._items)

    def item(self, index):
        return self._items[index]

    def addItem(self, item):
        if isinstance(item, str):
            self._items.append(MockListItem(item))
        else:
            self._items.append(item)

    def clear(self):
        self._items.clear()


def test_selected_items_tracker_basic():
    print("=== 测试 SelectedItemsTracker 基础功能 ===")
    tracker = SelectedItemsTracker()

    list_widget = MockListWidget([
        ("Python", True),
        ("AI", False),
        ("数据分析", True),
        ("机器学习", False),
    ])

    tracker.save(list_widget)

    assert len(tracker) == 2
    assert "Python" in tracker
    assert "数据分析" in tracker
    assert "AI" not in tracker

    selected = tracker.get_selected()
    assert selected == ["Python", "数据分析"]

    print("✓ 基础保存和查询功能通过")


def test_selected_items_tracker_restore():
    print("\n=== 测试 SelectedItemsTracker 恢复功能 ===")
    tracker = SelectedItemsTracker()

    list1 = MockListWidget([
        ("Python", True),
        ("AI", True),
        ("数据分析", False),
        ("机器学习", True),
    ])
    tracker.save(list1)

    list2 = MockListWidget([
        ("Python", False),
        ("AI", False),
        ("数据分析", False),
        ("机器学习", False),
        ("深度学习", False),
        ("大数据", False),
    ])

    tracker.restore(list2)

    assert list2.item(0).isSelected()
    assert list2.item(1).isSelected()
    assert not list2.item(2).isSelected()
    assert list2.item(3).isSelected()
    assert not list2.item(4).isSelected()
    assert not list2.item(5).isSelected()

    print("✓ 选中状态恢复功能通过")


def test_selected_items_tracker_filter_scenario():
    print("\n=== 测试 SelectedItemsTracker 过滤场景 ===")
    tracker = SelectedItemsTracker()

    all_tags = ["Python", "AI", "数据分析", "机器学习", "深度学习", "大数据", "Java", "C++"]
    list_widget = MockListWidget([(tag, False) for tag in all_tags])

    list_widget.item(0).setSelected(True)
    list_widget.item(1).setSelected(True)
    list_widget.item(3).setSelected(True)

    tracker.save(list_widget)

    assert tracker.get_selected() == ["AI", "Python", "机器学习"]

    filtered_tags = [t for t in all_tags if "P" in t.upper() or "学" in t]
    list_widget.clear()
    for tag in filtered_tags:
        list_widget.addItem(tag)

    assert list_widget.count() == 3
    assert filtered_tags == ["Python", "机器学习", "深度学习"]

    tracker.restore(list_widget)

    for i in range(list_widget.count()):
        item = list_widget.item(i)
        tag = item.data(32)
        if tag in ["Python", "机器学习"]:
            assert item.isSelected(), f"{tag} 应该被选中"
        else:
            assert not item.isSelected(), f"{tag} 不应该被选中"

    print("✓ 过滤后恢复选中状态通过")


def test_selected_items_tracker_update():
    print("\n=== 测试 SelectedItemsTracker.update() 增量更新 ===")
    tracker = SelectedItemsTracker()
    all_tags = ["Python", "AI", "数据分析", "机器学习", "深度学习", "Java"]

    tracker.add("Python")
    tracker.add("AI")
    tracker.add("机器学习")
    assert tracker.get_selected() == ["AI", "Python", "机器学习"]

    filtered_tags = ["Python", "AI", "数据分析"]
    list_widget = MockListWidget([
        ("Python", True),
        ("AI", False),
        ("数据分析", False),
    ])

    tracker.update(list_widget)

    assert "Python" in tracker
    assert "AI" not in tracker
    assert "机器学习" in tracker
    assert "数据分析" not in tracker
    assert tracker.get_selected() == ["Python", "机器学习"]

    list_widget.item(2).setSelected(True)
    tracker.update(list_widget)
    assert "数据分析" in tracker
    assert tracker.get_selected() == ["Python", "数据分析", "机器学习"]

    print("✓ 增量更新功能通过")


def test_selected_items_tracker_multiple_filters():
    print("\n=== 测试 SelectedItemsTracker 多次过滤 ===")
    tracker = SelectedItemsTracker()
    all_tags = ["Python编程", "AI人工智能", "数据分析", "机器学习", "深度学习", "大数据处理", "Java开发", "C++编程"]

    list_widget = MockListWidget([(tag, False) for tag in all_tags])
    list_widget.item(0).setSelected(True)
    list_widget.item(1).setSelected(True)
    list_widget.item(4).setSelected(True)
    list_widget.item(6).setSelected(True)

    expected = sorted(["AI人工智能", "Python编程", "Java开发", "深度学习"])
    tracker.save(list_widget)
    print(f"  初始保存: {tracker.get_selected()}")
    assert tracker.get_selected() == expected

    for filter_text in ["p", "a", "编程", "数据", ""]:
        filtered = [t for t in all_tags if filter_text.lower() in t.lower()]
        list_widget.clear()
        for tag in filtered:
            list_widget.addItem(tag)

        tracker.restore(list_widget)

        for i in range(list_widget.count()):
            item = list_widget.item(i)
            tag = item.data(32)
            if tag in expected:
                assert item.isSelected(), f"过滤 '{filter_text}' 时 {tag} 应该被选中"
            else:
                assert not item.isSelected(), f"过滤 '{filter_text}' 时 {tag} 不应该被选中"

        tracker.update(list_widget)

    assert tracker.get_selected() == expected
    print("✓ 多次过滤后选中状态保持一致通过")


def test_selected_items_tracker_filter_then_modify():
    print("\n=== 测试过滤后修改选中状态 ===")
    tracker = SelectedItemsTracker()
    all_tags = ["Python编程", "Python进阶", "AI人工智能", "AI机器学习", "Java开发", "C++编程"]

    list_widget = MockListWidget([(tag, False) for tag in all_tags])
    list_widget.item(0).setSelected(True)
    list_widget.item(2).setSelected(True)
    tracker.save(list_widget)
    expected_filter_initial = sorted(["AI人工智能", "Python编程"])
    assert tracker.get_selected() == expected_filter_initial

    filtered = [t for t in all_tags if "python" in t.lower()]
    list_widget.clear()
    for tag in filtered:
        list_widget.addItem(tag)
    tracker.restore(list_widget)

    assert list_widget.count() == 2
    assert list_widget.item(0).isSelected()
    assert not list_widget.item(1).isSelected()

    list_widget.item(1).setSelected(True)
    tracker.update(list_widget)

    expected = sorted(["Python进阶", "Python编程", "AI人工智能"])
    assert tracker.get_selected() == expected

    list_widget.clear()
    for tag in all_tags:
        list_widget.addItem(tag)
    tracker.restore(list_widget)

    selected = []
    for i in range(list_widget.count()):
        if list_widget.item(i).isSelected():
            selected.append(list_widget.item(i).data(32))

    assert sorted(selected) == expected
    assert "Java开发" not in selected
    assert "C++编程" not in selected

    print("✓ 过滤后修改选中状态测试通过")


def test_selected_items_tracker_add_remove_clear():
    print("\n=== 测试 SelectedItemsTracker 增删清空 ===")
    tracker = SelectedItemsTracker()

    tracker.add("Python")
    tracker.add("AI")
    assert len(tracker) == 2
    assert "Python" in tracker
    assert "AI" in tracker

    tracker.remove("Python")
    assert len(tracker) == 1
    assert "Python" not in tracker
    assert "AI" in tracker

    tracker.clear()
    assert len(tracker) == 0
    assert "AI" not in tracker

    print("✓ 增删清空功能通过")


def test_filter_assembler_build_query_string():
    print("\n=== 测试 FilterAssembler.build_query_string ===")

    q = FilterAssembler.build_query_string()
    assert q == ""

    q = FilterAssembler.build_query_string(title="Python")
    assert q == "title:(Python)"

    q = FilterAssembler.build_query_string(title="Python", author="张三")
    assert q == "title:(Python) AND author:(张三)"

    q = FilterAssembler.build_query_string(
        title="Python",
        author="张三",
        publisher="清华出版社",
        description="入门教程"
    )
    assert q == "title:(Python) AND author:(张三) AND publisher:(清华出版社) AND description:(入门教程)"

    q = FilterAssembler.build_query_string(title="  Python  ", author="")
    assert q == "title:(Python)"

    print("✓ 查询字符串构建通过")


def test_filter_assembler_assemble_filters():
    print("\n=== 测试 FilterAssembler.assemble_filters ===")

    result = FilterAssembler.assemble_filters()
    assert result["query"] == ""
    assert result["formats"] == []
    assert result["tags"] == []
    assert result["date_start"] is None
    assert result["date_end"] is None
    assert result["min_size"] is None
    assert result["max_size"] is None

    result = FilterAssembler.assemble_filters(
        title="Python",
        author="张三",
        selected_formats=["epub", "pdf"],
        selected_tags=["编程", "AI"],
        date_start=date(2020, 1, 1),
        date_end=date(2024, 12, 31),
        min_size=1024 * 1024,
        max_size=50 * 1024 * 1024,
    )
    assert result["query"] == "title:(Python) AND author:(张三)"
    assert result["formats"] == ["epub", "pdf"]
    assert result["tags"] == ["编程", "AI"]
    assert result["date_start"] == date(2020, 1, 1)
    assert result["date_end"] == date(2024, 12, 31)
    assert result["min_size"] == 1024 * 1024
    assert result["max_size"] == 50 * 1024 * 1024

    print("✓ 筛选条件组装通过")


def test_filter_assembler_assemble_criteria():
    print("\n=== 测试 FilterAssembler.assemble_criteria ===")

    criteria = FilterAssembler.assemble_criteria(
        title="Python入门",
        author="张三",
        formats=["epub"],
        tags=["编程"],
        date_start=date(2023, 1, 1),
        min_size_bytes=convert_mb_to_bytes(1),
    )

    assert criteria.title == "Python入门"
    assert criteria.author == "张三"
    assert criteria.formats == ["epub"]
    assert criteria.tags == ["编程"]
    assert criteria.date_start == date(2023, 1, 1)
    assert criteria.min_size_bytes == convert_mb_to_bytes(1)

    assert criteria.has_any_keyword()
    assert criteria.has_any_filter()
    assert criteria.has_any()

    qs = criteria.to_query_string()
    assert "title:(Python入门)" in qs
    assert "author:(张三)" in qs
    assert "AND" in qs

    search_params = criteria.to_search_params()
    assert search_params["filter_formats"] == ["epub"]
    assert search_params["filter_tags"] == ["编程"]
    assert search_params["date_start"] == date(2023, 1, 1)

    print("✓ Criteria 组装通过")


def test_advanced_search_criteria_basic():
    print("\n=== 测试 AdvancedSearchCriteria 基础功能 ===")

    empty = AdvancedSearchCriteria()
    assert not empty.has_any_keyword()
    assert not empty.has_any_filter()
    assert not empty.has_any()
    assert empty.to_query_string() == ""

    only_keywords = AdvancedSearchCriteria(title="Python", author="张三")
    assert only_keywords.has_any_keyword()
    assert not only_keywords.has_any_filter()
    assert only_keywords.has_any()

    only_filters = AdvancedSearchCriteria(formats=["epub"], tags=["AI"])
    assert not only_filters.has_any_keyword()
    assert only_filters.has_any_filter()
    assert only_filters.has_any()

    print("✓ 条件判断通过")


def test_advanced_search_criteria_to_from_dict():
    print("\n=== 测试 AdvancedSearchCriteria 序列化 ===")

    original = AdvancedSearchCriteria(
        title="Python入门",
        author="张三",
        publisher="清华出版社",
        description="适合初学者",
        search_content=True,
        formats=["epub", "pdf"],
        tags=["Python", "编程"],
        date_start=date(2023, 1, 1),
        date_end=date(2024, 12, 31),
        min_size_bytes=convert_mb_to_bytes(1),
        max_size_bytes=convert_mb_to_bytes(100),
        languages=["zh", "en"],
        isbns=["978-1-2345-6789-0"],
    )

    d = original.to_dict()
    assert d["formats"] == ["epub", "pdf"]
    assert d["tags"] == ["Python", "编程"]
    assert d["criteria"]["title"] == "Python入门"
    assert d["criteria"]["author"] == "张三"

    restored = AdvancedSearchCriteria.from_dict(d)
    assert restored.title == original.title
    assert restored.author == original.author
    assert restored.publisher == original.publisher
    assert restored.description == original.description
    assert restored.formats == original.formats
    assert restored.tags == original.tags
    assert restored.date_start == original.date_start
    assert restored.date_end == original.date_end
    assert restored.min_size_bytes == original.min_size_bytes
    assert restored.max_size_bytes == original.max_size_bytes
    assert restored.languages == original.languages
    assert restored.isbns == original.isbns

    print("✓ 序列化和反序列化通过")


def test_advanced_search_criteria_to_search_params():
    print("\n=== 测试 AdvancedSearchCriteria to_search_params ===")

    criteria = AdvancedSearchCriteria(
        formats=["epub"],
        tags=["AI"],
        date_start=date(2023, 1, 1),
        date_end=date(2024, 12, 31),
        min_size_bytes=1024 * 1024,
        max_size_bytes=50 * 1024 * 1024,
    )

    params = criteria.to_search_params()
    assert params["filter_formats"] == ["epub"]
    assert params["filter_tags"] == ["AI"]
    assert params["date_start"] == date(2023, 1, 1)
    assert params["date_end"] == date(2024, 12, 31)
    assert params["min_size"] == 1024 * 1024
    assert params["max_size"] == 50 * 1024 * 1024

    empty_criteria = AdvancedSearchCriteria()
    params2 = empty_criteria.to_search_params()
    for v in params2.values():
        assert v is None

    print("✓ to_search_params 通过")


def test_size_conversion():
    print("\n=== 测试大小转换函数 ===")

    bytes_val = convert_mb_to_bytes(5)
    assert bytes_val == 5 * 1024 * 1024

    mb_val = convert_bytes_to_mb(5 * 1024 * 1024)
    assert mb_val == 5.0

    assert format_file_size(0) == "0.0 B"
    assert format_file_size(1023) == "1023.0 B"
    assert format_file_size(1024) == "1.0 KB"
    assert format_file_size(1024 * 1024) == "1.0 MB"
    assert format_file_size(1024 * 1024 * 1024) == "1.0 GB"
    assert format_file_size(1024 * 1024 * 1024 * 1024) == "1.0 TB"

    print("✓ 大小转换通过")


def test_get_selected_in_filtered_state():
    print("\n=== 测试过滤状态下获取选中项 ===")
    tracker = SelectedItemsTracker()
    all_tags = ["A", "B", "C", "D", "E", "F", "G", "H"]

    list_widget = MockListWidget([(tag, False) for tag in all_tags])
    list_widget.item(0).setSelected(True)
    list_widget.item(1).setSelected(True)
    list_widget.item(2).setSelected(True)
    list_widget.item(3).setSelected(True)
    tracker.save(list_widget)

    assert sorted(tracker.get_selected()) == ["A", "B", "C", "D"]
    print(f"  初始选中: {sorted(tracker.get_selected())}")

    filtered = ["A", "B"]
    list_widget.clear()
    for tag in filtered:
        list_widget.addItem(tag)
    tracker.restore(list_widget)

    assert list_widget.item(0).isSelected()
    assert list_widget.item(1).isSelected()

    list_widget.item(0).setSelected(False)
    tracker.update(list_widget)

    selected = tracker.get_selected()
    assert sorted(selected) == ["B", "C", "D"]
    print(f"  过滤状态下取消A后选中: {sorted(selected)}")
    assert "A" not in selected
    assert "B" in selected
    assert "C" in selected
    assert "D" in selected

    list_widget.clear()
    for tag in all_tags:
        list_widget.addItem(tag)
    tracker.restore(list_widget)

    final_selected = []
    for i in range(list_widget.count()):
        if list_widget.item(i).isSelected():
            final_selected.append(list_widget.item(i).data(32))

    assert sorted(final_selected) == ["B", "C", "D"]
    assert "A" not in final_selected

    print("✓ 过滤状态下获取选中项测试通过")


def test_filter_then_search_then_expand():
    print("\n=== 测试过滤后取消勾选再展开 ===")
    tracker = SelectedItemsTracker()
    all_tags = ["Python编程", "Python进阶", "AI人工智能", "AI机器学习", "Java开发", "C++编程", "数据分析", "机器学习"]

    list_widget = MockListWidget([(tag, False) for tag in all_tags])
    list_widget.item(0).setSelected(True)
    list_widget.item(1).setSelected(True)
    list_widget.item(2).setSelected(True)
    list_widget.item(4).setSelected(True)
    tracker.save(list_widget)

    expected_after_save = sorted(["Python编程", "Python进阶", "AI人工智能", "Java开发"])
    assert tracker.get_selected() == expected_after_save
    print(f"  初始勾选: {expected_after_save}")

    filter_text = "python"
    filtered = [t for t in all_tags if filter_text.lower() in t.lower()]
    list_widget.clear()
    for tag in filtered:
        list_widget.addItem(tag)
    tracker.restore(list_widget)

    assert list_widget.count() == 2
    assert list_widget.item(0).isSelected()
    assert list_widget.item(1).isSelected()

    list_widget.item(0).setSelected(False)
    tracker.update(list_widget)

    assert "Python编程" not in tracker
    assert "Python进阶" in tracker
    assert "AI人工智能" in tracker
    assert "Java开发" in tracker
    print(f"  过滤后取消Python编程，保留: {tracker.get_selected()}")

    selected_from_tracker = tracker.get_selected()
    assert len(selected_from_tracker) == 3

    list_widget.clear()
    for tag in all_tags:
        list_widget.addItem(tag)
    tracker.restore(list_widget)

    final_selected = []
    for i in range(list_widget.count()):
        if list_widget.item(i).isSelected():
            final_selected.append(list_widget.item(i).data(32))

    expected_final = sorted(["Python进阶", "AI人工智能", "Java开发"])
    assert sorted(final_selected) == expected_final
    print(f"  展开后选中: {sorted(final_selected)}")
    assert "Python编程" not in final_selected

    print("✓ 过滤后取消勾选再展开测试通过")


def test_real_world_scenario():
    print("\n=== 测试真实场景：用户勾选标签后过滤 ===")

    all_tags = [
        "Python编程", "Python进阶", "Python数据分析",
        "AI人工智能", "AI机器学习", "AI深度学习",
        "Java基础", "JavaWeb开发",
        "C++高性能", "C++游戏开发",
        "数据结构", "算法导论",
        "数据库原理", "MySQL实战",
    ]

    tracker = SelectedItemsTracker()
    list_widget = MockListWidget([(tag, False) for tag in all_tags])

    list_widget.item(0).setSelected(True)
    list_widget.item(1).setSelected(True)
    list_widget.item(3).setSelected(True)
    list_widget.item(9).setSelected(True)

    expected_initial = sorted(["Python编程", "Python进阶", "AI人工智能", "C++游戏开发"])
    tracker.save(list_widget)
    before_filter = tracker.get_selected()
    print(f"  过滤前选中: {before_filter}")
    assert len(before_filter) == 4
    assert before_filter == expected_initial

    filter_text = "Python"
    filtered = [t for t in all_tags if filter_text.lower() in t.lower()]

    list_widget.clear()
    for tag in filtered:
        list_widget.addItem(tag)
    tracker.restore(list_widget)

    visible_selected = []
    for i in range(list_widget.count()):
        if list_widget.item(i).isSelected():
            visible_selected.append(list_widget.item(i).data(32))

    print(f"  过滤 '{filter_text}' 后可见选中: {visible_selected}")
    assert visible_selected == ["Python编程", "Python进阶"]

    tracker.update(list_widget)
    after_filter = tracker.get_selected()
    print(f"  过滤后tracker中: {after_filter}")
    assert len(after_filter) == 4

    list_widget.clear()
    for tag in all_tags:
        list_widget.addItem(tag)
    tracker.restore(list_widget)

    final_selected = []
    for i in range(list_widget.count()):
        if list_widget.item(i).isSelected():
            final_selected.append(list_widget.item(i).data(32))

    print(f"  展开完整列表后选中: {final_selected}")
    assert sorted(final_selected) == expected_initial

    print("✓ 真实场景测试通过")


def run_all_tests():
    print("=" * 70)
    print("测试筛选条件保留和组装模块")
    print("=" * 70)

    test_selected_items_tracker_basic()
    test_selected_items_tracker_restore()
    test_selected_items_tracker_filter_scenario()
    test_selected_items_tracker_update()
    test_selected_items_tracker_multiple_filters()
    test_selected_items_tracker_filter_then_modify()
    test_selected_items_tracker_add_remove_clear()
    test_filter_assembler_build_query_string()
    test_filter_assembler_assemble_filters()
    test_filter_assembler_assemble_criteria()
    test_advanced_search_criteria_basic()
    test_advanced_search_criteria_to_from_dict()
    test_advanced_search_criteria_to_search_params()
    test_size_conversion()
    test_get_selected_in_filtered_state()
    test_filter_then_search_then_expand()
    test_real_world_scenario()

    print("\n" + "=" * 70)
    print("✅ 所有测试通过！")
    print("=" * 70)


if __name__ == "__main__":
    run_all_tests()
