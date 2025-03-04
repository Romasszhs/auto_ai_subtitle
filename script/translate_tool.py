from translate import Translator
import re
import threading


def __translate(translator, text, n):
    """
    翻译单行文本
    :param translator: 翻译器实例
    :param text: 待翻译文本
    :param n: 行号
    :return: 翻译后的文本
    """
    if text == "" or text == '\n':
        return text

    text = text.rstrip('\n')
    # 如果是纯数字行(字幕序号),直接返回
    if re.match(r"^[0-9]+$", text):
        return add_newline_if_missing(text)

    # 如果是时间轴行,直接返回
    if re.match(r"\d{2}:\d{2}:\d{2},\d{3}\s-->\s\d{2}:\d{2}:\d{2},\d{3}", text):
        return add_newline_if_missing(text)

    # 翻译字幕内容
    return add_newline_if_missing(translator.translate(text))


def add_newline_if_missing(s):
    """
    确保字符串以换行符结尾
    :param s: 输入字符串
    :return: 确保以换行符结尾的字符串
    """
    if not s.endswith('\n'):
        s += '\n'
    return s


def translate_task(lines, translator_fun, result_map, i, translator):
    """
    单个翻译线程的任务函数
    :param lines: 待翻译的文本行列表
    :param translator_fun: 翻译函数
    :param result_map: 存储翻译结果的字典
    :param i: 线程ID
    :param translator: 翻译器实例
    """
    print("thread id: ", i, "lines num: ", len(lines))
    result_map[i] = [translator_fun(translator, line, n) for n, line in enumerate(lines)]


def translate_file(translator_fun, file1, file2, thread_nums, translator=None):
    """
    翻译整个文件
    :param translator_fun: 翻译函数
    :param file1: 源文件路径
    :param file2: 目标文件路径
    :param thread_nums: 线程数
    :param translator: 翻译器实例
    """
    with open(file1, 'r', encoding='utf-8') as f1, open(file2, 'w', encoding='utf-8') as f2:
        lines = f1.readlines()
        print("translate file total lines: ", len(lines))
        result = get_translate_result(lines, thread_nums, translator, translator_fun)
        f2.writelines(result)
        print("\ntranslate write file done")


def get_translate_result(lines, thread_nums, translator, translator_fun):
    """
    获取多线程翻译结果
    :param lines: 待翻译的文本行列表
    :param thread_nums: 线程数
    :param translator: 翻译器实例
    :param translator_fun: 翻译函数
    :return: 合并后的翻译结果列表
    """
    result_map = get_translate_threads_result(lines, thread_nums, translator, translator_fun)
    result = []
    for key in sorted(result_map):
        result.extend(result_map.get(key))
    return result


def get_translate_threads_result(lines, thread_nums, translator, translator_fun):
    """
    启动多线程进行翻译并获取结果
    :param lines: 待翻译的文本行列表
    :param thread_nums: 线程数
    :param translator: 翻译器实例
    :param translator_fun: 翻译函数
    :return: 包含各线程翻译结果的字典
    """
    result_map = {}
    threads = []
    n = len(lines) // thread_nums
    for i in range(1, thread_nums + 1):
        threads.append(
            threading.Thread(target=translate_task, args=(
                get_split_lines(i, lines, n, thread_nums), translator_fun, result_map, i, translator)))
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    return result_map


def get_split_lines(i, lines, n, thread_nums):
    """
    获取当前线程需要处理的文本行
    :param i: 线程ID
    :param lines: 所有文本行
    :param n: 每个线程处理的行数
    :param thread_nums: 总线程数
    :return: 当前线程需要处理的文本行列表
    """
    if n * i <= len(lines):
        split_line = lines[(i - 1) * n:i * n]
    else:
        split_line = lines[(i - 1) * n:]
    if i == thread_nums and n * i < len(lines):
        split_line = lines[(i - 1) * n:]
    return split_line


def do_translate(file1, file2, form, to, thread_nums):
    """
    执行文件翻译的主函数
    :param file1: 源文件路径
    :param file2: 目标文件路径
    :param form: 源语言
    :param to: 目标语言
    :param thread_nums: 线程数
    """
    translator = Translator(from_lang=form, to_lang=to)
    translate_file(__translate, file1, file2, thread_nums, translator)


if __name__ == '__main__':
    do_translate('test.srt', 'test1.srt', 'ja', 'zh')