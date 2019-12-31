#!/usr/bin/env python3
#coding:utf-8

import sys
import time
from io import BytesIO


class MP4(object):
	def __init__(self, file_name):
		self.fileName = file_name

	def _hex(self, byte):
		bio = BytesIO(byte)
		txt = ''
		while True:
			s = bio.read(1)
			if s == b'': break
			txt = txt + '%02X ' % int(ord(s))
		bio.close()
		return txt

	def _bin(self, data, size):
		return "%s" % (bin(self._int(data))[2:size + 2])

	def _int(self, data):
		return int(data.hex(), 16)

	def _str(self, data):
		return data.decode('utf-8')

	def _time(self, data):
		return time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime(self._int(data)))

	def _read(self, bio, dic):
		while True:
			size = bio.read(4)
			if size == b'':break
			size = self._int(size)
			data = bio.read(size - 4)
			tp = self._str(data[:4])
			self._parser(tp, dic, data[4:])

	def _parser(self, name, dic, data):
		if name == 'moov': out = self._moov(data)
		elif name == 'mvhd': out = self._mvhd(data)
		elif name == 'trak': out = self._trak(data)
		elif name == 'mdia': out = self._media(data)
		elif name == 'mdhd': out = self._mdhd(data)
		elif name == 'minf': out = self._minf(data)
		elif name == 'hdlr': out = self._hdlr(data)
		elif name == 'vmhd': out = self._vmhd(data)
		elif name == 'dinf': out = self._dinf(data)
		elif name == 'dref': out = self._dref(data)
		elif name == 'stbl': out = self._stbl(data)
		elif name == 'stts': out = self._stts(data)
		elif name == 'stss': out = self._stss(data)
		elif name == 'stsd': out = self._stsd(data)
		elif name == 'stco': out = self._stco(data)
		elif name == 'stsz': out = self._stsz(data)
		elif name == 'stsc': out = self._stsc(data)
		elif name == 'mdat': out = {}
		#else:out = {'data':self._hex(data)}
		else:out = {}

		if (name in dic):
			if isinstance(dic[name], dict):dic[name]=[dic[name], out]
			else:dic[name].append(out)
		else:dic[name] = out
		return dic

	def _sample_info(self, data):
		bio = BytesIO(data)
		dic = {
			'type':self._str(bio.read(4)),
			'version':self._int(bio.read(1))
		}

		if 'esds' == dic['type']:
			#Flags [3byte]
			dic['flag']=self._int(bio.read(3))
			#Tag [1byte]
			dic['tag-03'] = self._hex(bio.read(1))
			#ES Descriptor Length [1 - 4 byte Variable]
			#MPEG-4 specification ISO/IEC FDIS 14496-1
			dic['length-03'] = self._hex(bio.read(1))
			#ES_ID [2byte]
			dic['es_id'] = self._hex(bio.read(2))
			#-------- [ 1byte ] -------------
			dic['info'] = self._hex(bio.read(1))
			#StreamDependence Flage [1bit]
			#URL_Flag 				[1bit]
			#OCRstreamFlag 			[1bit]
			#StreamPriority			[5bits]
			#--------------------------------
			dic['tag-04'] = self._hex(bio.read(1))
			#Tag 					[1byte]
			dic['length-04'] = self._hex(bio.read(1))
			#Length 			  	[1 - 4 byte Variable]
			#ObjectType Indication	[1byte]
			dic['objectType_indication'] = self._hex(bio.read(1))
			#-------- [ 1byte ] -------------
			dic['type'] = self._hex(bio.read(1))
			#StreamType			  	[6bits]
			#Upstream				[1bit]
			#Reserved				[1bit]
			#--------------------------------
			dic['BufferSizeDB'] = self._hex(bio.read(3))
			#BufferSizeDB			[3byte]
			dic['MaxBitrate'] = self._hex(bio.read(4))
			#MaxBitrate				[4byte]
			dic['AvgBitrate'] = self._hex(bio.read(4))
			#AvgBitrate				[4byte]
			dic['tag-05'] = self._hex(bio.read(1))
			#Tag					[1byte]
			dic['length-05'] = self._int(bio.read(1))
			#Length 				[1 - 4 byte Variable]
			dic['info_data'] = self._hex(bio.read(dic['length-05']))
			#Info data 				[Variable]
			dic['tag-06'] = self._hex(bio.read(1))
			#Tag 					[1byte]
			dic['length-06'] = self._int(bio.read(1))
			#Length 				[1 - 4 byte Variable]
			dic['Predfined'] = self._hex(bio.read(1))
			#Predfined				[1byte]
		elif 'avcC' == dic['type']:
			#AVC Profile indication [1byte]
			bio.read(1)
			#Profile compatibility	[1byte]
			bio.read(1)
			#AVC Level indication	[1byte]
			bio.read(1)
			#-------- [ 1byte ] -------------
			#Reserved [6bits]
			#Length Size Minus One [2bits] NALU Length Field Byte -1
			bio.read(1)
			#--------------------------------
			#-------- [ 1byte ] -------------
			#Reserved [3bits]
			#SPS Count [5bits]
			count = self._int(bio.read(1)) & 31
			#--------------------------------
			dic['sps'] = []
			for i in range(0, count):
				#Sequence Parameter Set Length [2byte]
				sps_len = self._int(bio.read(2))
				dic['sps'].append(self._hex(bio.read(sps_len)))

			#PPS Count [1byte]
			count = self._int(bio.read(1))

			dic['pps'] = []
			for i in range(0, count):
				#Picture Parameter Set Length [2byte]
				pps_len = self._int(bio.read(2))
				dic['pps'].append(self._hex(bio.read(pps_len)))

		bio.close()
		return dic

	def _sample_parse(self, data):
		bio = BytesIO(data)

		dic = {
			'type':self._str(bio.read(4))
		}

		bio.read(1 * 6) 									#Reserved
		bio.read(2)		 									#Data-reference-index
		bio.read(2)		 									#Pre_defined
		bio.read(2)		 									#Reserved
		bio.read(4 * 3)	 									#Pre_defined

		if 'mp4v' == dic['type'] or 'avc1' == dic['type']:	#Sample_Video_Info
			dic['width']  = self._int(bio.read(2))			#Width
			dic['height'] = self._int(bio.read(2))			#Height
			dic['horiz_resolution']=self._hex(bio.read(4))	#Hresolution
			dic['verti_resolution']=self._hex(bio.read(4))	#Vresolution
			bio.read(4)		 								#Reserved
			dic['frame_count']=self._int(bio.read(2))		#FrameCount
			bio.read(1 * 32) 								#Compressonrname
			dic['depth']=self._hex(bio.read(2))				#Depth
			bio.read(2) 									#Pre_defined
			size = self._int(bio.read(4))
			dic['conf'] = self._sample_info(bio.read(size))
		elif 'mp4a' == dic['type']:
			dic['timescale']=self._int(bio.read(2))			#TimeScale
			bio.read(2)										#Reserved
			size = self._int(bio.read(4))
			dic['conf'] = self._sample_info(bio.read(size))
		bio.close()
		return dic

	def _sample(self, timeoffset, duration):
		atom = self.dic()['atom']

		traks = atom['moov']['trak']
		#sampling
		sample = {}
		for trak in traks:
			type = trak['mdia']['hdlr']['handler-type']
			stbl = trak['mdia']['minf']['stbl']
			stsz = stbl['stsz']['entry']
			stsd = stbl['stsd']['entry'][0]	#Chunk Offset
			b = 0
			for t in stsz:
				b += t['entry_size']
			out = self._sampling(trak, timeoffset, duration)
			out = {
				'sample':out,
				'info':{
					'duration':trak['mdia']['mdhd']['duration'],
					'timescale':trak['mdia']['mdhd']['timescale'],
					'sample-count':len(stsz),
					'total-size':b,
					'type':stsd['type']
				}
			}
			if type == 'vide':
				out['info']['pps'] = stsd['conf']['pps'][0]
				out['info']['sps'] = stsd['conf']['sps'][0]
				sample['video'] = out
			elif type == 'soun':
				sample['audio'] = out

		return sample

	def _make_sample_info(self, stsc, stco, stsz):
		info = []
		pos = 0
		count = stsc[pos]['sample_per_chunk']
		index = stsc[pos]['first_chunk_index']
		offset = stco[index - 1]['chunk_offset']
		for num in range(len(stsz)):
			size = stsz[num]['entry_size']
			#FIND OFFSET
			if num == count: # pos start 1, array start 0
				pos += 1 #stsc next position
				if index + 1 < stsc[pos]['first_chunk_index']:
					pos -= 1	#stsc current position
					index += 1
				else:
					index = stsc[pos]['first_chunk_index']

				offset = stco[index - 1]['chunk_offset']
				count += stsc[pos]['sample_per_chunk']

			sample = {
				# pos start 1, array start 0
				"offet":offset,
				#array start 0
				"size":size
			}
			#offet is move by sample size
			offset += size
			info.append(sample)

		return info

	def _make_sample_keyframe_info(self, stbl):
		info = []
		stss = stbl['stss']['entry'] #KeyFrame Info

		for obj in stss:
			info.append(obj['sample-number'])
		return info

	def _sampling(self, trak, offset, duration):
		sample = []
		type = trak['mdia']['hdlr']['handler-type']

		if type != 'vide' and type != 'soun':
			return

		mdhd = trak['mdia']['mdhd']
		stbl = trak['mdia']['minf']['stbl']
		stco = stbl['stco']['entry']	#Chunk Offset
		stsz = stbl['stsz']['entry']	#Sample Size
		stsc = stbl['stsc']['entry']	#Sample Count Per Chunk
		stts = stbl['stts']['entry']	#Sample Count PlayTime

		sample_info = self._make_sample_info(stsc, stco, stsz)
		keyframe = self._make_sample_keyframe_info(stbl) if type == 'vide' else []

		timescale = mdhd['timescale']
		a_time = 0	#TOTAL TIME
		time = 0	#TS TIME
		min = offset * timescale
		max = (offset + duration) * timescale
		sample_num = 0

		for data in stts:
			for n in range(data['count']):
				#TODO : 2018-11-27
				a_time += data['delta']
				if a_time > max: break
				if a_time > min:
					pack = {
						"id": sample_num,
						"type": str(type),
						"time": time,
						"timescale" : timescale,
						"chunk_offset": sample_info[sample_num]['offet'],
						"sample_size": sample_info[sample_num]['size']
					}

					if keyframe:
						pack['keyframe'] = sample_num + 1 in keyframe

					sample.append(pack)
					time += data['delta']

				sample_num += 1

		return sample

	def _atom(self):
		FH = open(self.fileName, 'rb')
		dic = {}
		size = 4
		data = FH.read(size)
		length = self._int(data)

		while True:
			head = self._str(FH.read(size))		#TYPE
			#if head == 'mdat':break			#Do not need!
			data = FH.read(length - len(data) - size)	#ALL - LEN(4) - TYPE(4)
			self._parser(head, dic, data)		#PARSER
			data = FH.read(size)				#READ LEN(4)
			if data == b'': break				#NONE
			length = self._int(data)				#LEN(4) BYTE TO INT

		FH.close()
		return dic

	def _moov(self, moov):
		bio = BytesIO(moov)
		dic = {}
		self._read(bio, dic)
		bio.close()
		return dic

	def _mvhd(self, mvhd):
		bio = BytesIO(mvhd)
		dic = {
			'version':self._int(bio.read(1)),
			'flag':self._int(bio.read(3))
		}

		s = 8 if dic['version'] else 4
		dic['create_time']=self._time(bio.read(s))
		dic['modification_time']=self._time(bio.read(s))
		dic['timescale']=self._int(bio.read(s))
		dic['duration']=self._int(bio.read(s))

		#Reserved
		bio.read(4)
		bio.read(2)
		bio.read(2)
		bio.read(8)
		bio.read(4 * 9)
		bio.read(4 * 6)
		#--Reserved

		#A 32-bit integer that indicates a value to use for the track ID number of the next track added to this movie. Note that 0 is not a valid track ID value.
		dic['next-track-id'] = self._int(bio.read(4))
		bio.close()
		return dic

	def _tkhd(self, tkhd):
		bio = BytesIO(tkhd)
		dic = {}
		head = bio.read(4).decode('utf-8')
		dic[head] = {
			'version':self._int(bio.read(1)),
			'flag':self._int(bio.read(3))
		}

		s = 8 if dic[head]['version'] else 4
		dic[head]['create_time']=self._time(bio.read(s))
		dic[head]['modification_time']=self._time(bio.read(s))
		dic[head]['track-id'] = self._int(bio.read(4))
		bio.read(4)
		dic[head]['duration']=self._int(bio.read(4))
		bio.read(4 * 3)
		bio.read(2)
		bio.read(2)
		bio.read(4 * 9)
		bio.read(4)
		bio.read(4)
		bio.close()
		return dic

	def _trak(self, trak):
		bio = BytesIO(trak)
		size = self._int(bio.read(4))
		tkhd = bio.read(size - 4)
		dic = self._tkhd(tkhd)
		self._read(bio, dic)
		bio.close()
		return dic

	def _media(self, media):
		bio = BytesIO(media)
		dic = {}
		self._read(bio, dic)
		bio.close()
		return dic

	def _mdhd(self, mdhd):
		bio = BytesIO(mdhd)
		dic = {
			'version':self._int(bio.read(1)),
			'flag':self._int(bio.read(3))
		}

		s = 8 if dic['version'] else 4
		dic['create_time']=self._time(bio.read(s))
		dic['modification_time']=self._time(bio.read(s))
		dic['timescale']=self._int(bio.read(s))
		dic['duration']=self._int(bio.read(s))
		dic['language']=self._bin(bio.read(2), 15)
		bio.close()
		return dic

	def _minf(self, minf):
		bio = BytesIO(minf)
		dic = {}
		self._read(bio, dic)
		bio.close()
		return dic

	def _hdlr(self, hdlr):
		bio = BytesIO(hdlr)
		dic = {
			'version':self._int(bio.read(1)),
			'flag':self._int(bio.read(3))
		}
		bio.read(4)	#Reserved
		dic['handler-type']=self._str(bio.read(4))
		bio.close()
		return dic

	def _vmhd(self, vmhd):
		bio = BytesIO(vmhd)
		dic = {
			'version':self._int(bio.read(1)),
			'flag':self._int(bio.read(3))
		}
		bio.read(8) #Reserved
		bio.close()
		return dic

	def _dinf(self, dinf):
		bio = BytesIO(dinf)
		dic = {}
		self._read(bio, dic)
		bio.close()
		return dic

	def _dref(self, dref):
		bio = BytesIO(dref)
		dic = {
			'version':self._int(bio.read(1)),
			'flag':self._int(bio.read(3))
		}

		count = self._int(bio.read(4)) #Entry-Count

		dic['entry'] = []
		for i in range(0, count):
			size = self._int(bio.read(4))
			data = bio.read(size)
			dic['entry'].append({
				'type':self._str(data[:4]),
				'version':self._int(data[4:5]),
				'flag':self._int(data[5:8])
			})
		bio.close()
		return dic

	def _stbl(self, stbl):
		bio = BytesIO(stbl)
		dic = {}
		self._read(bio, dic)
		bio.close()
		return dic

	def _stsd(self, stsd):
		bio = BytesIO(stsd)
		dic = {
			'version':self._int(bio.read(1)),
			'flag':self._int(bio.read(3)),
		}

		count = int(bio.read(4).hex(), 16) #Entry-Count

		dic['entry'] = []
		for i in range(0, count):
			size = self._int(bio.read(4))
			data = bio.read(size)
			dic['entry'].append(self._sample_parse(data))
		bio.close()
		return dic

	def _stss(self, stss):
		bio = BytesIO(stss)
		dic = {
			'version':self._int(bio.read(1)),
			'flag':self._int(bio.read(3))
		}

		count = self._int(bio.read(4)) #Entry-Count

		dic['entry'] = []
		for i in range(0, count):
			dic['entry'].append({
				'sample-number':self._int(bio.read(4)),
			})

		bio.close()
		return dic

	def _stts(self, stts):
		bio = BytesIO(stts)
		dic = {
			'version':self._int(bio.read(1)),
			'flag':self._int(bio.read(3))
		}

		count = self._int(bio.read(4)) #Entry-Count

		dic['entry'] = []
		for i in range(0, count):
			dic['entry'].append({
				'count':self._int(bio.read(4)),
				'delta':self._int(bio.read(4))
			})

		bio.close()
		return dic

	def _stsc(self, stsc):
		bio = BytesIO(stsc)
		dic = {
			'version':self._int(bio.read(1)),
			'flag':self._int(bio.read(3))
		}

		count = self._int(bio.read(4)) #Entry-count

		dic['entry'] = []
		for i in range(0, count):
			dic['entry'].append({
				'first_chunk_index':self._int(bio.read(4)),
				'sample_per_chunk':self._int(bio.read(4)),
				'sample_description_index':self._int(bio.read(4))
			})
		bio.close()
		return dic

	def _stco(self, stco):
		bio = BytesIO(stco)
		dic = {
			'version':self._int(bio.read(1)),
			'flag':self._int(bio.read(3)),
		}

		count = self._int(bio.read(4)) #Entry-count

		dic['entry'] = []
		for i in range(0, count):
			dic['entry'].append({
				'chunk_offset':self._int(bio.read(4))
			})
		bio.close()
		return dic

	def _stsz(self, stsz):
		bio = BytesIO(stsz)
		dic = {
			'version':self._int(bio.read(1)),
			'flag':self._int(bio.read(3)),
			'sample_size':self._int(bio.read(4))
		}

		count = self._int(bio.read(4)) #Entry-count

		dic['entry'] = []
		for i in range(0, count):
			size = bio.read(4)
			if size:
				size = self._int(size)
				dic['entry'].append({
					'entry_size':size
				})
		bio.close()
		return dic

	def dic(self):
		return{
			"filename": self.fileName,
			"atom":self._atom()
		}

if __name__ == '__main__':
	print(MP4('./2019-12-24T09-55-01.mp4').dic())
