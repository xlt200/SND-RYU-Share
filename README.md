# SND-RYU-Share
 執行時需要在ryu-manager哪裡添加observe-links指令，否則會獲取不了網路拓撲
 內定是每秒都會獲取一次每個switch的狀態，同時測一次現在每個link的頻寬，注意裡面頻寬的單位是 Mbyte/sec
 現在新增的流表有idle_timeout, 一旦流表閒置時間超過了指定時間後便會被自動刪除（預定是10秒）
