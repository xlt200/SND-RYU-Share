# SND-RYU-Share
## BWShotestPath.py
 執行時需要在ryu-manager哪裡添加observe-links指令，否則會獲取不了網路拓撲 <br><br/>
 內定是每秒都會獲取一次每個switch的狀態，同時測一次現在每個link的頻寬，注意裡面頻寬的單位是 Mbits/sec <br><br/>
 現在新增的流表有idle_timeout, 一旦流表閒置時間超過了指定時間後便會被自動刪除（預定是10秒）<br><br/>
## ShortestPath.py
  根據BWShortestPath.py改寫，比起BWShortestPath多了可以偵測link-delay的功能（但並沒有用來做任何事），同時又修改了部份原代碼 <br><br/>
  實現方式參考了：
  * <https://www.sdnlab.com/16859.html> 
  * <https://github.com/muzixing/ryu/tree/master/ryu/app/network_awareness>  
  <a/>
  <br/>
  要注意其中對於源代碼switches.py的修改，一開始的delay會有點高，過一會后就會恢復降低
