def allocate_thread(num: int, total_threads: int = 10) -> int:
    """
    基于模数运算的线程分配器
    :param num: 自然数输入（>=0）
    :param total_threads: 总线程数（默认10）
    :return: 分配的线程索引（0~total_threads-1）
    """
    return num % total_threads

# 测试用例
if __name__ == '__main__':
    test_numbers = [101, 202, 315, 478, 599,100]
    for n in test_numbers:
        print(f"数字{n} -> 线程{allocate_thread(n)}")