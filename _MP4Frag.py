import time
from io import BytesIO
from multiprocessing import Process,Pipe

class MP4Frag():
	_FTYP = bytes([0x66, 0x74, 0x79, 0x70])# ftyp
	_MOOV = bytes([0x6d, 0x6f, 0x6f, 0x76])# moov
	_MOOF = bytes([0x6d, 0x6f, 0x6f, 0x66])# moof
	_MFRA = bytes([0x6d, 0x66, 0x72, 0x61])# mfra
	_MDAT = bytes([0x6d, 0x64, 0x61, 0x74])# mdat
	_MP4A = bytes([0x6d, 0x70, 0x34, 0x61])# mp4a
	_AVCC = bytes([0x61, 0x76, 0x63, 0x43])# avcC
	def __init__(self, pipe):
		self._parseChunk = self._findFtyp
		self._rpipe = pipe
		self._pipe,self._wpipe = Pipe(duplex=True)
		self._process = Process(target=self._proc, name = "mp4frag")
	def _int(self, data):
		#return int(data.hex(), 16)
		return int.from_bytes(data,byteorder='big',signed=False)
	def _str(self, data):
		return data.decode('utf-8')
	def pipe(self):
		return self._wpipe

	def _proc(self):
		while True:
			self._transform()
			time.sleep(0.1)

	def _transform(self):
		chunk = self._rpipe.read()
		self._parseChunk(chunk)

	def _bsconcate(self, li, leng):
		res = bytes()
		for	i in li:
			res += i
		if leng > len(res):
			return res
		return res[:leng]

	def _findFtyp(self, chunk):
		chunkLength = len(chunk)
		if (chunkLength < 8 or chunk.find(MP4Frag._FTYP) != 4):
			print("error: can not find ftyp")
			return
		self._ftypLength = self._int(chunk[:4])
		if (self._ftypLength < chunkLength):
			self._ftyp = chunk[:self._ftypLength]
			self._parseChunk = self._findMoov
			self._parseChunk(chunk[self._ftypLength:])
		elif (self._ftypLength == chunkLength):
			self._ftyp = chunk
			self._parseChunk = self._findMoov
		else:
			print("error: can not find ftyp")

	def _findMoov(self, chunk):
		chunkLength = len(chunk)
		if (chunkLength < 8 or chunk.find(MP4Frag._MOOV) != 4):
			print("error: can not find moov")
			return
		moovLength = self._int(chunk[:4])
		if (moovLength < chunkLength):
			self._parseMoov(self._ftyp + chunk)
			del self._ftyp
			del self._ftypLength
			self._parseChunk = self._findMoof
			self._parseChunk(chunk[moovLength:])
		elif (moovLength == chunkLength):
			self._parseMoov(self._ftyp + chunk)
			del self._ftyp
			del self._ftypLength
			self._parseChunk = self._findMoof
		else:
			print("error: can not find moov")

	def _findMoof(self, chunk):
		if (hasattr(self, '_moofBuffer')):
			self._moofBuffer.append(chunk)
			chunkLength = len(chunk)
			self._moofBufferSize += chunkLength
			if (self._moofLength == self._moofBufferSize):
				self._moof = self._bsconcate(self._moofBuffer, self._moofLength)
				del self._moofBuffer
				del self._moofBufferSize
				self._parseChunk = self._findMdat
			elif (self._moofLength < self._moofBufferSize):
				self._moof = self._bsconcate(self._moofBuffer, self._moofLength)
				sliceIndex = chunkLength - (self._moofBufferSize - self._moofLength)
				del self._moofBuffer
				del self._moofBufferSize
				self._parseChunk = self._findMdat
				self._parseChunk(chunk[sliceIndex:])
		else:
			chunkLength = len(chunk)
			if (chunkLength < 8 or chunk.find(MP4Frag._MOOF) != 4):
				#ffmpeg occasionally pipes corrupt data, lets try to get back to normal if we can find next MOOF box before attempts run out
				mfraIndex = chunk.find(MP4Frag._MFRA)
				if mfraIndex != -1:
					return
				self._moofHunts = 0
				self._moofHuntsLimit = 40
				self._parseChunk = self._moofHunt
				self._parseChunk(chunk)
				return
			self._moofLength = self._int(chunk[:4])
			if self._moofLength == 0:
				print("error, Bad data from input stream reports moof length of 0")
				return
			if self._moofLength < chunkLength:
				self._moof = chunk[:self._moofLength]
				self._parseChunk = self._findMdat
				self._parseChunk(chunk[self._moofLength:])
			elif self._moofLength == chunkLength:
				self._moof = chunk
				self._parseChunk = self._findMdat
			else:
				self._moofBuffer = [chunk]
				self._moofBufferSize = chunkLength

	def _findMdat(self, chunk):
		if (hasattr(self, '_mdatBuffer')):
			self._mdatBuffer.append(chunk)
			chunkLength = len(chunk)
			self._mdatBufferSize += chunkLength
			if (self._mdatLength == self._mdatBufferSize):
				self._setSegment(self._bsconcate([self._moof].expend(self._mdatBuffer), self._moofLength + self._mdatLength))
				del self._moof
				del self._mdatBuffer
				del self._mdatBufferSize
				del self._mdatLength
				del self._moofLength
				self._parseChunk = self._findMoof
			elif (self._mdatLength < self._mdatBufferSize):
				self._setSegment(self._bsconcate([self._moof].expend(self._mdatBuffer), self._moofLength + self._mdatLength))
				sliceIndex = chunkLength - (self._mdatBufferSize - self._mdatLength)
				del self._moof
				del self._mdatBuffer
				del self._mdatBufferSize
				del self._mdatLength
				del self._moofLength
				self._parseChunk = self._findMoof
				self._parseChunk(chunk[sliceIndex:])
		else:
			chunkLength = len(chunk)
			if (chunkLength < 8 or chunk.find(MP4Frag._MDAT) != 4):
				print("error: mdat no found")
				return
			self._mdatLength = self._int(chunk[:4])
			if (self._mdatLength > chunkLength):
				self._mdatBuffer = [chunk]
				self._mdatBufferSize =chunkLength
			elif (self._mdatLength < chunkLength):
				self._setSegment(self._bsconcate([self._moof, chunk], self._moofLength + chunkLength))
				del self._moof
				del self._moofLength
				del self._mdatLength
				self._parseChunk = self._findMoof
			else:
				self._setSegment(self._bsconcate([self._moof, chunk], self._moofLength + self._mdatLength))
				sliceIndex = self._mdatLength
				del self._moof
				del self._moofLength
				del self._mdatLength
				self._parseChunk = self._findMoof
				self._parseChunk(chunk[sliceIndex:])

	def _moofHunt(self, chunk):
		if (self._moofHunts < self._moofHuntsLimit):
			self._moofHunts += 1
			index = chunk.find(MP4Frag._MOOF)
			if (index > 3 and len(chunk) > index + 3):
				del self._moofHunts
				del self._moofHuntsLimit
				self._parseChunk = self._findMoof
				self._parseChunk(chunk[index - 4:])
		else:
			print("error: ")

	def _parseMoov(self, chunk):
		self._initialization = chunk
		audioString = ''
		if (self._initialization.find(MP4Frag._MP4A) != -1):
			audioString = ', mp4a.40.2'
		index = self._initialization.find(MP4Frag._AVCC)
		if index == -1:
			print("error: can not find vacc codec info")
			return
		index += 5
		self._mime = "video/mp4; codecs='avc1.%s%s'"%( \
			self._initialization[index:index + 3].hex().upper(), \
			audioString \
		)
		self._timestamp = int(round(time.time() * 1000))
		if (hasattr(self, '_hlsList') and hasattr(self, '_hlsListInit')):
			m3u8 = '#EXTM3U\n'
			m3u8 += '#EXT-X-VERSION:7\n'
			#m3u8 += '#EXT-X-ALLOW-CACHE:NO\n'
			m3u8 += '#EXT-X-TARGETDURATION:1\n'
			m3u8 += '#EXT-X-MEDIA-SEQUENCE:0\n'
			m3u8 += '#EXT-X-MAP:URI="init-%s.mp4"\n'%self._hlsBase
			self._m3u8 = m3u8

	def _setSegment(self, chunk):
		self._segment = chunk
		currentTime = int(round(time.time() * 1000))
		self._duration = max((currentTime - self._timestamp)/1000, 1)
		self._timestamp = currentTime
		if (hasattr(self, '_hlsList')):
			self._sequence += 1
			self._hlsList.append({'sequence': self._sequence,
				'name':'%s%d'%(self._hlsBase, self._sequence),
				'segment':self._sequence,
				'duration':self._duration})
			while (len(self._hslist) > self._hlsListSize):
				self._hslist.pop(index=0)
			m3u8 = '#EXTM3U\n';
			m3u8 += '#EXT-X-VERSION:7\n';
			#m3u8 += '#EXT-X-ALLOW-CACHE:NO\n';
			m3u8 += '#EXT-X-TARGETDURATION:%d\n'%Math.round(this._duration)
			m3u8 += '#EXT-X-MEDIA-SEQUENCE:%d\n'%this._hlsList[0].sequence
			m3u8 += '#EXT-X-MAP:URI="init-%s.mp4"\n'%this._hlsBase