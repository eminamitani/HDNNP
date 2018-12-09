# -*- coding: utf-8 -*-

import argparse
from pathlib import Path


def get_parser():
    parser = argparse.ArgumentParser(description='High Dimensional Neural Network Potential',
                                     fromfile_prefix_chars='@',
                                     formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument('--debug', '-d', action='store_true', default=False,
                        help='If this flag is set, MPI subprocesses also print their stdout')

    # subcommands
    subparsers = parser.add_subparsers(dest='mode', metavar='RUNNING MODE')
    train_parser = subparsers.add_parser(
        'train',
        formatter_class=argparse.RawTextHelpFormatter,
        help='Train a HDNNP to optimize energies and/or forces.')
    predict_parser = subparsers.add_parser(
        'predict',
        formatter_class=argparse.RawTextHelpFormatter,
        help='Predict energies and/or forces for atomic structures using trained HDNNP.')
    subparsers.add_parser(
        'param-search',
        formatter_class=argparse.RawTextHelpFormatter,
        help='Search for the best set of hyperparameters using Bayesian Optimization method.')
    subparsers.add_parser(
        'sym-func',
        formatter_class=argparse.RawTextHelpFormatter,
        help='Calculate symmetry functions of atomic structures.')

    # for train mode
    train_parser.add_argument(
        '--verbose', '-v', action='store_true', default=False,
        help='Plot total RMSE graph.\n'
             'This flag increases processing time.')
    train_parser.add_argument(
        '--resume', '-r', metavar='DIR', type=Path,
        help='Resume training from given atomic configuration directory,\n'
             'which must contain `trainer_snapshot.npz` and `interim_result.pickle`.')

    # for predict mode
    predict_parser.add_argument(
        'value', metavar='VALUE', type=str, nargs='+',
        choices=['energy', 'force', 'E', 'F'],
        help='Values to be predicted for atomic structures using trained HDNNP.\n'
             '`energy` can be abbreviated as `E`, and `force` as `F`.')
    predict_parser.add_argument(
        '--poscars', '-p', metavar='FILE', required=True, type=Path, nargs='+',
        help='Path to one or more POSCAR format files.')
    predict_parser.add_argument(
        '--masters', '-m', metavar='FILE', required=True, type=Path,
        help='Path to a trained masters model, which is created by running `hdnnpy train`.')
    predict_parser.add_argument(
        '--write', '-w', metavar='FILE',
        type=Path, nargs='?', default=None, const='./prediction.dat',
        help='Write predicted value into a text file. (default: %(default)s)')

    return parser.parse_args()
