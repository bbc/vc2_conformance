import sys
import logging

import numpy as np
from imageio import imwrite

from toy_vc2 import decode_sequence, pic_num, Y, C1, C2


def main():
    logging.basicConfig(level=logging.DEBUG)
    
    filename = sys.argv[1]
    
    with open(filename, "rb") as f:
        video_parameters, decoded_pictures = decode_sequence(f)
    
    w = video_parameters.frame_width
    h = video_parameters.frame_height
    
    for picture in decoded_pictures:
        luma = picture[Y]
        im = np.zeros((h, w))
        for y in range(h):
            for x in range(w):
                im[y, x] = luma[y][x] / float(video_parameters.luma_excursion)
        imwrite("/tmp/out_{}.png".format(picture[pic_num]), im)


if __name__ == "__main__":
    main()

