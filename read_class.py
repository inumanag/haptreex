import random
import copy
import math
##from helpers import *

class READ(object):
        ## for normal reads, the read_dict doesnt include starts of reads
        def __init__(self,read,count,read_num):
                self.read = read
                self.count = count
                self.keys = sorted(self.read.keys())
                self.use = True
                self.genomic_region = None
                self.size = len(self.keys)
                self.read_num = read_num
                self.mini_reads = self.make_mini_reads()
                self.special_key = self.keys[0]
                self.rates = {0:.5,1:.5}

        def __eq__(self,other):
                return (self.read==other.read and self.read_num == other.read_num)

        def __len__(self):
                return len(self.read)

                

        def make_mini_reads(self):
            mini_read_dict = {}
            mini_read = copy.copy(self.read)
            for key in reversed(sorted(self.keys)):
                mini_read_dict[key] = mini_read
                mini_read = copy.copy(mini_read)
                mini_read.pop(key)
            return mini_read_dict
                


def sample_from_reads(reads):
    new_reads = []
    for read in reads:
        if read.size >0:
            new_reads.append(read)
        else:
            choice = random.choice(read.keys)
            new_read = READ({choice:read.read[choice]},read.read_num)
            new_reads.append(new_read)
    return new_reads
            

