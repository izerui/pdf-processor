import os
import time
import numpy as np

from fitz import fitz

if __name__ == '__main__':
    doc = fitz.open('tmp/FB14-KX23120262-23-049-A 封板.pdf')
    doc.save(os.path.join('tmp', f"tmp-{int(time.time())}.pdf"))

    array = np.array([[(10, 2, 4, 5), (4, 2, 1, 6)], [(100, 20, 40, 50), (14, 22, 11, 16)],
                      [(102, 23, 44, 55), (41, 22, 13, 64)]])
    str = np.array2string(array, separator=',')
    # print(str)

    s = '10,2,4,5;4,2,1,6 100,20,40,50;14,22,11,16 102,23,44,55;41,22,13,64'
    marks = list(
        map(
            lambda x: list(
                map(
                    lambda y: list(
                        map(
                            lambda z: z,
                            y.split(',')
                        )
                    ),
                    x.split(';')
                )
            ),
            s.split(' ')
        )
    )
    pass