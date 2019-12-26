#! /bin/bash

#start ffserver
ffserver -f /etc/ffserver.conf >> /dev/null & \

#run 3 ffmpeg, they transfer data to each other via pipe

#start 1st ffmpeg to pull a stream and decode it
ffmpeg -threads 2 -loglevel warning -analyzeduration 1000000 -probesize 1000000 -fflags +igndts -i "rtmp://media3.sinovision.net:1935/live/livestream" -update 1 -r 15 -f rawvideo -pix_fmt yuv420p -s 720x406 pipe:1 | \
#start 2nd ffmpeg to put logo with "horse race lamp" into frame
ffmpeg -threads 2 -thread_queue_size 10k -f rawvideo -pix_fmt yuv420p -s 720x406 -i - -i ffmpeg-logo.png -filter_complex "overlay=x='if(gte(t,0),-w+(mod(n,W+w))+1,NAN)':y=0" -f rawvideo -pix_fmt yuv420p -s 720x406 pipe:1 | \
#start 3rd ffmpeg to encode and push frame to ffserver
ffmpeg -thread_queue_size 10k -hwaccel auto -threads 2 -loglevel warning -analyzeduration 1000000 -probesize 1000000 -fflags +igndts -f rawvideo -pix_fmt yuv420p -s 720x406 -r 15 -i - -vcodec libx264 -crf 23 -maxrate 1M -bufsize 2M -movflags +faststart -tune zerolatency -profile:v baseline -s 720x406 -g 60 -r 15 -copytb 1 http://localhost:8090/feed1.ffm

#Now run VLC to play rtsp://localhost:5454/test
