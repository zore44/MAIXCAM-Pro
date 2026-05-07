from maix import audio, app, time  
import numpy as np  
import math  
  
def calculate_decibel(pcm_data):  
    """  
    计算PCM音频数据的分贝值  
    """  
    if len(pcm_data) == 0:  
        return 0  
      
    # 将字节数据转换为16位有符号整数  
    audio_data = np.frombuffer(pcm_data, dtype=np.int16)  
      
    # 计算RMS (均方根)  
    rms = np.sqrt(np.mean(audio_data.astype(np.float32) ** 2))  
      
    # 避免log(0)的情况  
    if rms == 0:  
        return 0  
      
    # 转换为分贝值 (参考值为32767，16位音频的最大值)  
    db = 20 * math.log10(rms / 32767.0)  
      
    # 调整到合理的分贝范围 (通常环境音在30-90dB)  
    db = max(0, db + 96)  # 96dB的偏移量  
      
    return db  
  
# 初始化录音器  
r = audio.Recorder(block=False)  # 非阻塞模式，不保存文件  
r.volume(100)  # 设置音量为100  
r.reset(True)   # 启用音频流  
  
print("开始检测声音分贝值，按Ctrl+C退出...")  
  
while not app.need_exit():  
    try:  
        # 录制50ms的音频数据  
        data = r.record(50)  
          
        if len(data) > 0:  
            # 计算分贝值  
            db_value = calculate_decibel(data) -60 
            print(f"当前声音分贝值: {db_value:.1f} dB")  
          
        time.sleep_ms(100)  # 100ms间隔检测  
          
    except KeyboardInterrupt:  
        break  
  
# 停止音频流  
r.reset(False)  
print("检测结束")