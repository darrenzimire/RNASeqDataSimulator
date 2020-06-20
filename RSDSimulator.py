#!/usr/bin/python3
# encoding =UTF-8

import os
import random
import numpy as np
import scipy as sp
import argparse
import pyfaidx
import gzip
import pickle as pickle
from itertools import chain
from SequenceContainer import ReadContainer

# Parsing all input arguments

parser = argparse.ArgumentParser(description='RNASeqDesigner Version 1')
# parser.add_argument('-h', type=int, required=True, default=100, metavar='<i>', help='help function')
parser.add_argument('-r',               type=int,                 required=True,              default=101, metavar='<int>', help='Read length')
parser.add_argument('-n',               type=int,                 required=True, default=10000,            metavar='<int>', help='Number of reads to simulate')
parser.add_argument('-f',               type=str,                 required=True,                           metavar='<str>', help='Reference transcriptome file')
parser.add_argument('-s',               type=int,                 required=False, default=1223,            metavar='<int>', help='Random seed for reproducibility')
parser.add_argument('-o',               type=str,                 required=True,                           metavar='<str>', help='Output prefix')
parser.add_argument('-seqmodel',        type=str,                 required=True,                           metavar='<str>', help='Sequencing_model')
parser.add_argument('-countModel',      type=str,                 required=False,                          metavar='<str>', help='transcript expression count model')
parser.add_argument('-er',              type=float,               required=False, default=-1,              metavar='<int>', help='Error rate')
parser.add_argument('-FL', nargs=2,     type=int,                 required=False, default=(250, 25),       metavar=('<int>', '<int>'),help='Fragment length distribution parameters')
parser.add_argument('-SE', action='store_true',                   required=False, help='Flag for producing single-end reads ')
parser.add_argument('-PE', action='store_true',                   required=False, help='Flag for producing paired-end reads')


args = parser.parse_args()

(fragment_mean, fragment_std) = args.FL
ref = args.f
readlen = args.r
readtot = args.n
SEED = args.s
output = args.o
sqmodel = args.seqmodel
countModel = args.countModel
SE = args.SE
PE = args.PE
SE_RATE = args.er

paired = False
single = False
counts = False
profile = False

if fragment_mean != None and fragment_std != None:
    paired = True

if PE != None:
    paired = True

if countModel != None:
    profile = True

if SE != None:
    single = True

np.random.seed(SEED)
NB = np.round(sp.random.negative_binomial(n=1, p=0.1, size=10000))
NB_model = [1 if x == 0 else x for x in NB]

print('reading reference file: ' + str(ref) + "\n")

pyfaidx.Faidx(ref)
print('Indexing reference file....' + "\n")

# Search current directory for index file and read into programme
indexFile = ''
for file in os.listdir('.'):
    if file.endswith('.fai'):
        indexFile = (os.path.join('.', file))

SE_CLASS = ReadContainer(readlen, sqmodel, SE_RATE)


def scalereadnum(read_counts, n):
    sc = []
    scale = []
    total = sum(read_counts)
    for i in read_counts:
        x = i / total
        scale.append(x)
    for i in scale:
        y = n * i
        sc.append(round(y))
    scaled_counts = [1 if x == 0 else x for x in sc]

    return scaled_counts


# Process and read in all models

if countModel != None:
    tissue_profile = open(countModel, 'rb')
    transcript_ids = pickle.load(tissue_profile, encoding='latin1')
    count_table = pickle.load(tissue_profile, encoding='latin1')


def normdist(low, high=None, size=None):
    """
    Description
    This function generates random numbers according to a specified distribution
    Parameters
    low (int): The lowest value to sample
    high (int) the upper bound for sampling
    Return: Returns a vector of numbers drawn from a user-specified distribution
    """
    np.random.seed(SEED)
    counts = np.round(np.random.uniform(low=0, high=high, size=size))

    return counts

def parseIndexRef(indexFile):
    """
    Description:
    Read in sequence data from reference index FASTA file returns a list of transcript IDs
    offset, seqLen, position
    Parameters
     - indexFile (str): The index file generated by the program, written to the current directory
    Return: The function returns a list of tuples containing the transcript id, start and end offset of the transcript sequence
    """
    ref_inds = []
    filt_ref_inds = []
    fai = open(indexFile, 'r')
    for line in fai:
        splt = line[:-1].split('\t')
        header = '@' + splt[0]
        seqLen = int(splt[1])
        offset = int(splt[2])
        lineLn = int(splt[3])
        nLines = seqLen / lineLn

        if seqLen % lineLn != 0:
            nLines += 1
        ref_inds.append([header, offset, offset + seqLen + nLines])
    
    for i in ref_inds:
        if i[3] >= 100:
            filt_ref_inds.append(i)
    for x in filt_ref_inds:
        i.pop(3)
    fai.close()
    return filt_ref_inds

def samplingtranscripts(ids):
    """"
    Description: This function randomly sample from all reference transcripts
    Parameters: ids (list of tuples) It takes as input all reference transcripts offsets
    Returns: This function returns a subset of transcript ids to be sampled from
    """
    random.seed(SEED)
    numreads = readtot
    sampledtranscripts = random.sample(ids, numreads)

    return sampledtranscripts


def getseq(key, start=1, end=None):
    """
    Description
    Get a sequence by key coordinates are 1-based and end is inclusive
    Parameters:
        key:
        start:
        end:
    Returns:
    """

    if end != None and end < start:
        return ""
    start -= 1
    seek = start

    # if seek is past sequence then return empty sequence
    if seek >= end:
        return ""

    # seek to beginning
    infile = open(ref, 'r')
    infile.seek(seek)

    # read until end of sequence
    header = ''
    seq = []
    if end == None:
        lenNeeded = util.INF
    else:
        lenNeeded = end - start

    len2 = 0
    while len2 < lenNeeded:
        line = infile.readline()
        if line.startswith(">") or len(line) == 0:
            break
        seq.append(header + line.rstrip())
        len2 += len(seq[-1])
        if len2 > lenNeeded:
            seq[-1] = seq[-1][:-int(len2 - lenNeeded)]
            break
    seq = "".join(seq)
    return seq


def processTransIDs(ids):
    """"
    Description:
    This function take as input a list of transcript ids and converts it to a dictionary
    Parameters:
        ids (list of tuples): List of transcript ids
    Returns: The function returns a dictionary of transcript id as key and start and end position as value
    """

    Transseq = []
    header = []
    transcriptID = {i: [j, k] for i, j, k in ids}
    ID = transcriptID.keys()
    for k in ID:
        header.append(k)
    pos = transcriptID.values()
    for i in pos:
        start = i[0]
        end = i[1]
        seq = getseq(ID, start, end)
        Transseq.append(seq)

    new_dict = {k: v for k, v in zip(header, Transseq)}
    return new_dict

def GenerateRead(seq, readLen, n, *args):
    """
    Description:
    This function truncates transcript sequences by a specified read length.
    Parameters:
    :param seq: Transcript sequence randomly sampled from the input reference transcriptome file
    :param readLen: The user-specified read length

    :return: The function returns a list of all truncated sequences
    """
    global endpos

    startpos = []
    seqLen = len(seq)
  
    for ag in args:

        if ag == 'SE':

            v = np.round(np.random.uniform(low=1, high=seqLen, size=100000))
            spos = random.choices(v, k=n)

            startpos.append(spos)
            endpos = [i + readLen for i in startpos[0]]

        else:
            
            nmax = [seqLen - i - 1 for i in readLen]
            v = np.round(np.random.uniform(low=1, high=nmax, size=n))
            spos = (random.choices(v, k=len(readLen)))
            startpos.append(spos)
            
    return startpos, seqLen

def sample_qualscore(sequencingModel):
    (myQual, myErrors) = SE_CLASS.getSequencingErrors(sequencingModel)
    return myQual


random.seed(1234)


def main():

    global quality_strings

    ref_transcript_ids = parseIndexRef(indexFile)

    if SE == True:

        sample_trans_ids = []
        COUNTS = []
        quality_strings = []
        reads = []
        ID = []
        Seq = []
        spos = []
        epos = []
        record = []

        if single == True and countModel == None:
            print('Simulating single-end reads....' + "\n")
            print('No transcript profile model detected!!'+ "\n")
            print('Simulating default transcript profile' + "\n")

            counts = np.random.choice(NB_model, size=readtot, replace=True).tolist()

            scaled_counts = scalereadnum(counts, readtot)

            samptransids = random.choices(ref_transcript_ids, k=len(scaled_counts))

            sample_trans_ids.append(samptransids)
            COUNTS.append(scaled_counts)

        elif single == True and countModel != None:
            print('Simulating single-end reads' + "\n")
            print('Detected transcript profile model.....' + "\n")
            print('Simulating empirical transcript profile' + "\n")
            counts_s = scalereadnum(count_table, readtot)
            samptransids = random.choices(ref_transcript_ids, k=len(counts_s))

            sample_trans_ids.append(samptransids)
            COUNTS.append(counts_s)

        data = list(chain.from_iterable(sample_trans_ids))
        for j in data:
            p = processTransIDs([tuple(j)])

            for id, seq in p.items():
                ID.append(id)
                Seq.append(seq)

        D = list(chain.from_iterable(COUNTS))
        for s, r in zip(Seq, D):
            readinfo = GenerateRead(s, readlen, r, 'SE')
            startpos = readinfo[0]
            endpos = readinfo[1]
            spos.append(startpos)
            epos.append(endpos)
        
        for k, l, s in zip(spos, epos, Seq):
            R = [k,l,s]
            record.append(R)
        
        for i in record:
            start = i[0]
            end   = i[1]
            sequence = i[2]
            
            for p, q, v in zip(start, end, sequence):
                read = sequence[int(p):int(q)]
                qdata = sample_qualscore(sequencingModel=sqmodel)
                reads.append(read)
                quality_strings.append(qdata)
                
        print('writing reads to output file...' + "\n")
        with gzip.open(output + '.fastq.gz', 'w') as handle:
            for id, read, q in zip(ID, reads, quality_strings):
                handle.write('{}\n{}\n+\n{}\n'.format(id, read, q).encode())

        print('Simulation process completed ')
        
    elif PE != None:


        R1 = []
        R2 = []
        RFS = []
        COUNTS_P = []
        quality_strings = []
        ID = []
        Seq = []
        Fragments = []

        if paired == True and countModel == None:
            print('Generating paired-end reads.....' + "\n")
            print('Sampling counts from negative binomial model' + "\n")

            counts_NB = np.random.choice(NB_model, size=readtot, replace=True).tolist()
            counts_p = scalereadnum(counts_NB, readtot)
            COUNTS_P.append(counts_p)
        elif paired == True and countModel != None:
            print('Generating paired-end reads' + "\n")
            print('Simulating empirical transcript profile.....' + "\n")

            counts_p = scalereadnum(count_table, readtot)
            COUNTS_P.append(counts_p)

        FS = np.random.normal(fragment_mean, fragment_std, 100000).astype(int).tolist()
        for i in COUNTS_P[0]:
            randomFS = random.choices(FS, k=i)
            RFS.append(randomFS)

        samptransids = random.choices(ref_transcript_ids, k=len(COUNTS_P[0]))
        f_startpos = []
        f_endpos = []
        for j in (samptransids):

            p = processTransIDs([j])
            for id, seq in p.items():
                ID.append(id)
                Seq.append(seq)
        for s, r in zip(Seq, RFS):
            readinfo = GenerateRead(s, r, len(r), 'PE')
            startpos = list(chain.from_iterable(readinfo[0]))
            f_startpos.append(startpos)
            endpos = [readlen + i for i in startpos]
            f_endpos.append(endpos)
            
        for k, l, s in zip(f_startpos, f_endpos, Seq):
            R = [k,l,s]
            record.append(R)
        
        for i in record:
            start = i[0]
            end = i[1]
            sequence = i[2]
            
            for p,e,s in zip(start, end, sequence):
                frag = sequence[int(p):int(e)]
                Fragments.append(frag)
            
            frag = s[k:l]
            Fragments.append(frag)
            qdata = sample_qualscore(sequencingModel=sqmodel)
            quality_strings.append(qdata)

        for i in Fragments:
            read1 = i[:readlen]
            read2 = i[-readlen:]
            R1.append(read1)
            R2.append(read2)
      
        
        print('writing reads to output file' + "\n")
        with gzip.open(output +'_R1.fastq.gz', 'wb') as f1, gzip.open(output + '_R2.fastq.gz', 'wb') as f2:
            for id, reads1, reads2, q in zip(ID, R1, R2, quality_strings):
                f1.write('{}\n{}\n+\n{}\n'.format(id, reads1, q).encode())
                f2.write('{}\n{}\n+\n{}\n'.format(id, reads2, q).encode())
        print('Simulation completed ')

if __name__ == '__main__':
    main()



























