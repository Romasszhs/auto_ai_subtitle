import re
import torch
import whisper
import sys
import time
from tqdm import tqdm


def reformat_time(second):
    m, s = divmod(second, 60)
    h, m = divmod(m, 60)
    hms = "%02d:%02d:%s" % (h, m, str('%.3f' % s).zfill(6))
    hms = hms.replace('.', ',')
    return hms


def write_srt(seg, srt_path):
    with open(srt_path, 'w', encoding='utf-8') as f:
        write_content = [str(n + 1) + '\n'
                         + reformat_time(i['start'])
                         + ' --> '
                         + reformat_time(i['end']) + '\n'
                         + i['text'] + '\n\n'
                         for n, i in enumerate(seg)]
        f.writelines(write_content)


def hf_to_whisper_states(text):
    text = re.sub('.layers.', '.blocks.', text)
    text = re.sub('.self_attn.', '.attn.', text)
    text = re.sub('.q_proj.', '.query.', text)
    text = re.sub('.k_proj.', '.key.', text)
    text = re.sub('.v_proj.', '.value.', text)
    text = re.sub('.out_proj.', '.out.', text)
    text = re.sub('.fc1.', '.mlp.0.', text)
    text = re.sub('.fc2.', '.mlp.2.', text)
    text = re.sub('.fc3.', '.mlp.3.', text)
    text = re.sub('.fc3.', '.mlp.3.', text)
    text = re.sub('.encoder_attn.', '.cross_attn.', text)
    text = re.sub('.cross_attn.ln.', '.cross_attn_ln.', text)
    text = re.sub('.embed_positions.weight', '.positional_embedding', text)
    text = re.sub('.embed_tokens.', '.token_embedding.', text)
    text = re.sub('model.', '', text)
    text = re.sub('attn.layer_norm.', 'attn_ln.', text)
    text = re.sub('.final_layer_norm.', '.mlp_ln.', text)
    text = re.sub('encoder.layer_norm.', 'encoder.ln_post.', text)
    text = re.sub('decoder.layer_norm.', 'decoder.ln.', text)
    return text


def load_model_bin(model_path, device):
    # Load HF Model
    hf_state_dict = torch.load(model_path, map_location=torch.device(device))  # pytorch_model.bin file

    # Rename layers
    for key in list(hf_state_dict.keys())[:]:
        new_key = hf_to_whisper_states(key)
        hf_state_dict[new_key] = hf_state_dict.pop(key)

    # Init Whisper Model and replace model weights
    whisper_model = whisper.load_model('large')
    whisper_model.load_state_dict(hf_state_dict)
    return whisper_model


def do_whisper(audio, srt_path, language, hf_model_path, device):
    print("Loading model...")
    if hf_model_path == "":
        model = whisper.load_model("base")
    else:
        model = load_model_bin(hf_model_path, device)
    
    print("Starting transcription...")
    try:
        # 使用 tqdm 显示进度条
        with tqdm(total=100, desc="Transcribing", unit="%") as pbar:
            # 配置转录选项
            options = {
                "language": language,
                "task": "transcribe",
                "fp16": False,  # 强制使用 FP32
                "verbose": False
            }
            
            result = model.transcribe(audio, **options)
            pbar.update(100)  # 完成时更新到100%
        
        print("\nWriting SRT file...")
        write_srt(result['segments'], srt_path)
        print("Transcription completed successfully!")
        
    except Exception as e:
        print(f"\nError during transcription: {str(e)}")
        raise


if __name__ == '__main__':
    do_whisper(r"test.mp3", "test.srt", "", "pytorch_model.bin", 'cpu')
