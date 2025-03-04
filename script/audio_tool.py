import ffmpeg
import subprocess
import os
import sys

# def audio_extract(input, output):
# 	ffmpeg.input(input, vn=None).output(output).run()

# 解决中文路径ffmpeg无法运行的问题
def audio_extract(input_path, output_path):
	# 确保输出目录存在
	os.makedirs(os.path.dirname(output_path), exist_ok=True)
	
	# 检查ffmpeg是否安装
	try:
		subprocess.run(['ffmpeg', '-version'], capture_output=True, check=True)
	except subprocess.CalledProcessError:
		print("Error: FFmpeg is not installed or not in system PATH")
		sys.exit(1)
	except FileNotFoundError:
		print("Error: FFmpeg is not installed or not in system PATH")
		sys.exit(1)

	# 转换路径为绝对路径
	input_path = os.path.abspath(input_path)
	output_path = os.path.abspath(output_path)

	command = [
		'ffmpeg',
		'-y',              # 自动覆盖输出文件
		'-i', input_path,  # 输入文件
		'-vn',            # 禁用视频
		'-acodec', 'libmp3lame',  # 使用MP3编码器
		'-ar', '48000',   # 设置采样率为16kHz（whisper模型需要）
		'-ac', '2',       # 单声道
		'-ab', '192k',   # 比特率
		'-copyts',
		'-vsync','0',
		'-hide_banner',   # 隐藏ffmpeg版本信息
		output_path
	]
	
	try:
		# 使用subprocess.run执行命令
		process = subprocess.Popen(
			command,
			stdout=subprocess.PIPE,
			stderr=subprocess.PIPE,
			encoding='utf-8',
			errors='replace'
		)
		
		# 实时获取输出
		stdout, stderr = process.communicate()
		
		if process.returncode != 0:
			print(f"FFmpeg error occurred (return code {process.returncode}):")
			print(f"Command: {' '.join(command)}")
			print(f"Error output: {stderr}")
			raise subprocess.CalledProcessError(process.returncode, command, stderr)
			
		print("Audio extraction completed successfully")
		
	except subprocess.CalledProcessError as e:
		print(f"FFmpeg error occurred:")
		print(f"Command: {' '.join(command)}")
		print(f"Error output: {e.stderr}")
		raise
		
	except Exception as e:
		print(f"Unexpected error: {str(e)}")
		raise
			