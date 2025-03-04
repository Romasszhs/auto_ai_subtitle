from deep_translator import GoogleTranslator
import re
import threading
import time
from tqdm import tqdm
from queue import Queue, Empty
from threading import Lock
from collections import OrderedDict

# Language code mapping
LANGUAGE_CODE_MAP = {
    'ja': 'ja',      # Japanese
    'zh': 'zh-CN',   # Simplified Chinese
    'ko': 'ko',      # Korean
    'en': 'en'       # English
}

class SubtitleBlock:
    def __init__(self):
        self.index = ""
        self.timestamp = ""
        self.content = []
        self.blank_line = ""

    def is_complete(self):
        return self.index and self.timestamp and self.content

    def __str__(self):
        return f"{self.index}{self.timestamp}{''.join(self.content)}{self.blank_line}"

    def needs_translation(self):
        # 检查是否需要翻译（非空且不是时间戳）
        return any(line.strip() and not re.match(r"\d{2}:\d{2}:\d{2},\d{3}\s-->\s\d{2}:\d{2}:\d{2},\d{3}", line.strip()) for line in self.content)

def parse_subtitle_blocks(lines):
    blocks = []
    current_block = SubtitleBlock()
    
    for line in lines:
        if re.match(r"^\d+$", line.strip()):  # Index line
            if current_block.is_complete():
                blocks.append(current_block)
                current_block = SubtitleBlock()
            current_block.index = line
        elif re.match(r"\d{2}:\d{2}:\d{2},\d{3}\s-->\s\d{2}:\d{2}:\d{2},\d{3}", line.strip()):  # Timestamp
            current_block.timestamp = line
        elif line.strip() == "":  # Blank line
            current_block.blank_line = line
        else:  # Content line
            current_block.content.append(line)
    
    if current_block.is_complete():
        blocks.append(current_block)
    
    return blocks

class Translator:
    def __init__(self, from_lang='ja', to_lang='zh'):
        # Map language codes to supported format
        source_lang = LANGUAGE_CODE_MAP.get(from_lang, from_lang)
        target_lang = LANGUAGE_CODE_MAP.get(to_lang, to_lang)
        self.translator = GoogleTranslator(source=source_lang, target=target_lang)
        self.max_retries = 3
        self.retry_delay = 2  # 重试延迟秒数

    def translate(self, text):
        retries = 0
        while retries < self.max_retries:
            try:
                return self.translator.translate(text)
            except Exception as e:
                retries += 1
                if retries == self.max_retries:
                    print(f"\nTranslation error after {retries} retries: {str(e)}")
                    return text  # 返回原文
                print(f"\nRetrying translation ({retries}/{self.max_retries})...")
                time.sleep(self.retry_delay)

def translate_block(translator, block):
    """翻译字幕块的内容，保持结构不变"""
    translated_block = SubtitleBlock()
    translated_block.index = block.index
    translated_block.timestamp = block.timestamp
    translated_block.blank_line = block.blank_line
    
    translated_content = []
    for line in block.content:
        if line.strip() and not re.match(r"\d{2}:\d{2}:\d{2},\d{3}\s-->\s\d{2}:\d{2}:\d{2},\d{3}", line.strip()):
            translated_line = translator.translate(line.rstrip('\n'))
            translated_content.append(f"{translated_line}\n")
        else:
            translated_content.append(line)
    
    translated_block.content = translated_content
    return translated_block

class TranslationWorker:
    def __init__(self, blocks_to_translate, result_dict, lock, translator, progress_bar, worker_id, total_workers):
        self.blocks_to_translate = blocks_to_translate
        self.result_dict = result_dict
        self.lock = lock
        self.translator = translator
        self.progress_bar = progress_bar
        self.worker_id = worker_id
        self.total_workers = total_workers

    def process_tasks(self):
        # 只处理worker_id对应的模块的字幕块
        for block in self.blocks_to_translate:
            block_index = int(block.index.strip())
            if block_index % self.total_workers == self.worker_id:
                print(f"\n{'='*20} Thread-{self.worker_id} Processing Block {block_index} {'='*20}")
                print(f"Original content:")
                for line in block.content:
                    print(f"  {line.strip()}")
                # 为每个翻译请求添加唯一标识
                translated_block = self.translate_block_with_unique_id(block, block_index)
                with self.lock:
                    self.result_dict[block_index] = translated_block
                    self.progress_bar.update(1)

    def translate_block_with_unique_id(self, block, block_index):
        """使用唯一标识符翻译字幕块"""
        translated_block = SubtitleBlock()
        translated_block.index = block.index
        translated_block.timestamp = block.timestamp
        translated_block.blank_line = block.blank_line
        
        translated_content = []
        for i, line in enumerate(block.content):
            if line.strip() and not re.match(r"\d{2}:\d{2}:\d{2},\d{3}\s-->\s\d{2}:\d{2}:\d{2},\d{3}", line.strip()):
                # 为每行添加唯一标识符，翻译后再移除
                unique_id = f"[ID_{block_index}_{i}]"
                text_to_translate = f"{unique_id}{line.strip()}"
                print(f"\nThread-{self.worker_id} translating:")
                print(f"  Text with ID: {text_to_translate}")
                
                translated_text = self.translator.translate(text_to_translate)
                print(f"  Translated result: {translated_text}")
                
                # 移除唯一标识符
                translated_text = translated_text.replace(unique_id, "").strip()
                translated_content.append(f"{translated_text}\n")
            else:
                translated_content.append(line)
        
        translated_block.content = translated_content
        return translated_block

def translate_blocks_parallel(blocks, thread_nums, translator):
    # 筛选需要翻译的字幕块
    blocks_to_translate = [block for block in blocks if block.needs_translation()]
    
    # 创建线程安全的结果字典
    result_dict = OrderedDict()
    lock = Lock()
    
    # 创建进度条
    progress_bar = tqdm(total=len(blocks_to_translate), desc="Translating", unit="blocks")
    
    # 创建工作线程
    workers = []
    for i in range(thread_nums):
        worker = TranslationWorker(blocks_to_translate, result_dict, lock, translator, progress_bar, i, thread_nums)
        thread = threading.Thread(target=worker.process_tasks)
        workers.append(thread)
        thread.start()
    
    # 等待所有线程完成
    for worker in workers:
        worker.join()
    
    progress_bar.close()
    
    # 按原始顺序重建结果
    final_blocks = []
    for block in blocks:
        block_index = int(block.index.strip())
        if block_index in result_dict:
            final_blocks.append(result_dict[block_index])
        else:
            final_blocks.append(block)
    
    return final_blocks

def translate_file(file1, file2, thread_nums, translator):
    with open(file1, 'r', encoding='utf-8') as f1:
        lines = f1.readlines()
        print("Parsing subtitle blocks...")
        blocks = parse_subtitle_blocks(lines)
        print(f"Found {len(blocks)} subtitle blocks")
        
        translated_blocks = translate_blocks_parallel(blocks, thread_nums, translator)
        
        print("\nWriting translated subtitles...")
        with open(file2, 'w', encoding='utf-8') as f2:
            for block in translated_blocks:
                f2.write(str(block))
        print("Translation completed")

def do_translate(file1, file2, form, to, thread_nums):
    # 创建单一的翻译器实例
    translator = Translator(from_lang=form, to_lang=to)
    translate_file(file1, file2, thread_nums, translator)

if __name__ == '__main__':
    do_translate(r'C:\Users\35720\Downloads\auto_ai_subtitle\script\测试的日文字幕.srt', 
                r'C:\Users\35720\Downloads\auto_ai_subtitle\script\测试的日文字幕-zh.srt', 
                'ja', 'zh', 10)