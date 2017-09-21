# -*- coding: utf-8 -*-

import requests
from bottle import get, post, request, hook, route, response
from PIL import Image
import ssim
from imagehash import  dhash, whash, phash
import bottle

class ImageMatcher:
    def __init__(self, hamming_threshold = 9, ssim_threshold = 0.7):
        self.hamming_treshhold = hamming_threshold
        self.ssim_threshold = ssim_threshold

    def _GetImageData(self, url):
        data = {}
        data['image_data'] = Image.open(requests.get(url, stream=True).raw)
        data['resized_image_data'] = data['image_data'].resize((11,11),Image.ANTIALIAS)
        data['dhash'] = str(dhash(data['image_data']))
        data['phash'] = str(phash(data['image_data']))
        data['whash'] = str(whash(data['image_data']))
        return data


    def _Hamming(self, hex1, hex2):
        return bin(int(hex1, 16) ^ int(hex2, 16)).count('1')

    def _Match(self, images):
        for a_key, a_value in images.items():
            images[a_key]['matches'] = {}
            for b_key, b_value in images.items():
                if a_key != b_key:
                    dHamming = self._Hamming(a_value['dhash'], b_value['dhash'])
                    pHamming = self._Hamming(a_value['phash'], b_value['phash'])
                    wHamming = self._Hamming(a_value['whash'], b_value['whash'])
                    if all(x == 0 for x in (dHamming, pHamming, wHamming)):
                        images[a_key]['matches'][b_key] = 1
                    elif all(x <= self.hamming_treshhold for x in (dHamming, pHamming, wHamming)):
                        ssimScore = ssim.compute_ssim(a_value['resized_image_data'], b_value['resized_image_data'])
                        if ssimScore >= self.ssim_threshold:
                            images[a_key]['matches'][b_key] = ssimScore
        return images

    def _ProcessImages(self, urls):
        images = {}
        for url in urls:
            images[url] = self._GetImageData(url)
        return images

    def Match(self, urls):
        return self._Match(self._ProcessImages(urls))


if __name__ == "__main__":
    _allow_origin = '*'
    _allow_methods = 'PUT, GET, POST, DELETE, OPTIONS'
    _allow_headers = 'Authorization, Origin, Accept, Content-Type, X-Requested-With'

    _app = bottle.default_app()

    _image_matcher = ImageMatcher()

    @hook('after_request')
    def enable_cors():
        response.headers['Access-Control-Allow-Origin'] = _allow_origin
        response.headers['Access-Control-Allow-Methods'] = _allow_methods
        response.headers['Access-Control-Allow-Headers'] = _allow_headers


    @route('/', method='OPTIONS')
    @route('/<path:path>', method='OPTIONS')
    def options_handler(path=None):
        return

    @post('/image_matcher/', method=['POST'])
    def image_matcher():
        urls = request.json['urls']
        images = _image_matcher.Match(urls)
        for k, _ in images.items():
            del images[k]['image_data']
            del images[k]['resized_image_data']
        return images

    bottle.run(host='0.0.0.0', port=8000)

'''
{
"urls":["https://cdn-images-1.medium.com/max/1600/0*ieeOOOEXfY-q0Ucr.png","https://cdn-images-1.medium.com/max/1600/0*dMjl9teTjf5z4QjS.png", "https://cdn-images-1.medium.com/max/1600/0*C4X0A9U-OwTY2uCK.png"]
}
'''