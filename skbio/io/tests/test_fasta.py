# ----------------------------------------------------------------------------
# Copyright (c) 2013--, scikit-bio development team.
#
# Distributed under the terms of the Modified BSD License.
#
# The full license is in the file COPYING.txt, distributed with this software.
# ----------------------------------------------------------------------------

from __future__ import absolute_import, division, print_function
from future.utils.six import StringIO

from unittest import TestCase, main

from skbio import (BiologicalSequence, NucleotideSequence, DNA, RNA, Protein,
                   ProteinSequence)
from skbio import SequenceCollection, Alignment
from skbio.io import FASTAFormatError
from skbio.io.fasta import (
    _fasta_to_generator, _fasta_to_sequence_collection, _generator_to_fasta,
    _biological_sequence_to_fasta, _nucleotide_sequence_to_fasta,
    _dna_sequence_to_fasta, _rna_sequence_to_fasta,
    _protein_sequence_to_fasta, _sequence_collection_to_fasta,
    _alignment_to_fasta)
from skbio.util import get_data_path


class FASTAReaderTests(TestCase):
    def setUp(self):
        # store sequence generator (expanded into a list) that we expect to
        # obtain from reading, matched with the kwargs and filepaths that
        # should deserialize into the expected generator results
        self.empty = ([], {}, map(get_data_path, ['empty']))

        self.single = (
            [BiologicalSequence('ACGT-acgt.', id='seq1', description='desc1')],
            {},
            map(get_data_path, ['fasta_single_seq', 'fasta_max_width_1'])
        )

        self.multi = (
            [BiologicalSequence('ACGT-acgt.', id='seq1', description='desc1'),
             BiologicalSequence('A', id='_____seq__2_'),
             BiologicalSequence('AACGGuA', description='desc3'),
             BiologicalSequence('AcGtUTu'),
             BiologicalSequence('ACGTTGCAccGG'),
             BiologicalSequence('ACGUU'),
             BiologicalSequence(
                 'pQqqqPPQQQ', id='proteinseq',
                 description='detailed description \t\twith  new  lines')],
            {},
            map(get_data_path, ['fasta_multi_seq', 'fasta_max_width_5'])
        )

        # test constructor parameter, as well as odd labels (label only
        # containing whitespace, label description preceded by multiple spaces,
        # no id) and leading/trailing whitespace on sequence data
        self.odd_labels_different_type = (
            [Protein('DEFQfp'),
             Protein('SKBI', description='skbio')],
            {'constructor': ProteinSequence},
            map(get_data_path, ['fasta_prot_seqs_odd_labels'])
        )

        # sequences that can be loaded into a SequenceCollection or Alignment.
        # they are also a different type than BiologicalSequence in order to
        # exercise the constructor parameter
        self.sequence_collection_different_type = (
            [RNA('AUG'),
             RNA('AUC', id='rnaseq-1', description='rnaseq desc 1'),
             RNA('AUG', id='rnaseq-2', description='rnaseq desc 2')],
            {'constructor': RNA},
            map(get_data_path, ['fasta_sequence_collection_different_type'])
        )

        self.invalid_fps = map(lambda e: (get_data_path(e[0]), e[1]), [
            ('whitespace_only', 'without a FASTA header'),
            ('fasta_invalid_missing_header', 'without a FASTA header'),
            ('fasta_invalid_blank_line', 'blank or whitespace-only'),
            ('fasta_invalid_whitespace_only_line', 'blank or whitespace-only'),
            ('fasta_invalid_missing_seq_data_first', 'without sequence data'),
            ('fasta_invalid_missing_seq_data_middle', 'without sequence data'),
            ('fasta_invalid_missing_seq_data_last', 'without sequence data'),
        ])

    def test_fasta_to_generator_valid_files(self):
        for exp, kwargs, fps in (self.empty, self.single, self.multi,
                                 self.odd_labels_different_type,
                                 self.sequence_collection_different_type):
            for fp in fps:
                obs = list(_fasta_to_generator(fp, **kwargs))

                self.assertEqual(len(obs), len(exp))
                for o, e in zip(obs, exp):
                    self.assertTrue(o.equals(e))

    def test_fasta_to_generator_invalid_files(self):
        for fp, error_msg_regex in self.invalid_fps:
            with self.assertRaisesRegexp(FASTAFormatError, error_msg_regex):
                list(_fasta_to_generator(fp))

#    def test_fasta_to_sequence_collection(self):
#        for exp_list, kwargs, fps in (self.empty, self.single,
#                                      self.sequence_collection_different_type):
#            exp = SequenceCollection(exp_list)
#
#            for fp in fps:
#                obs = _fasta_to_sequence_collection(fp, **kwargs)
#
#                # TODO remove this custom equality testing code when
#                # SequenceCollection has an equals method (part of #656). We
#                # need this method to include IDs and description in the
#                # comparison (not part of SequenceCollection.__eq__).
#                self.assertEqual(obs, exp)
#                for o, e in zip(obs, exp):
#                    self.assertTrue(o.equals(e))


class FASTAWriterTests(TestCase):
    def setUp(self):
        self.bio_seq1 = BiologicalSequence(
            'ACGT-acgt.', id='seq1', description='desc1', quality=range(10))
        self.bio_seq2 = BiologicalSequence('A', id=' \n  \nseq \t2 ')
        self.bio_seq3 = BiologicalSequence('AACGGuA', description='desc3')
        self.nuc_seq = NucleotideSequence('AcGtUTu')
        self.dna_seq = DNA('ACGTTGCAccGG')
        self.rna_seq = RNA('ACGUU', quality=[42] * 5)
        self.prot_seq = Protein(
            'pQqqqPPQQQ', id='proteinseq',
            description='\ndetailed\ndescription \t\twith  new\n\nlines\n\n\n')

        seqs = [
            RNA('UUUU', id='s\te\tq\t1', description='desc\n1'),
            BiologicalSequence(
                'CATC', id='s\te\tq\t2', description='desc\n2'),
            Protein('sits', id='s\te\tq\t3', description='desc\n3')
        ]
        self.seq_coll = SequenceCollection(seqs)
        self.align = Alignment(seqs)

        def empty_gen():
            raise StopIteration()
            yield

        def single_seq_gen():
            yield self.bio_seq1

        # generate sequences with descriptions containing newlines (to test
        # description_newline_replacement)
        def newline_description_gen():
            yield self.prot_seq
            yield DNA('AGGAGAATA', id='foo', description='\n\n\n\n')

        # generate sequences with ids containing whitespace (to test
        # id_whitespace_replacement)
        def whitespace_id_gen():
            yield self.bio_seq2
            yield RNA('UA', id='\n\t \r', description='a\nb')

        # multiple sequences of mixed types, lengths, and metadata. lengths are
        # chosen to exercise various splitting cases when testing max_width
        def multi_seq_gen():
            for seq in (self.bio_seq1, self.bio_seq2, self.bio_seq3,
                        self.nuc_seq, self.dna_seq, self.rna_seq,
                        self.prot_seq):
                yield seq

        # store sequence generator to serialize, writer kwargs (if any), and
        # filepath of expected results
        self.objs_fps = map(lambda e: (e[0], e[1], get_data_path(e[2])), [
            (empty_gen(), {}, 'empty'),
            (single_seq_gen(), {}, 'fasta_single_seq'),
            (single_seq_gen(), {'max_width': 1}, 'fasta_max_width_1'),
            (multi_seq_gen(), {}, 'fasta_multi_seq'),
            (multi_seq_gen(), {'max_width': 5}, 'fasta_max_width_5'),
            (newline_description_gen(),
             {'description_newline_replacement': ':-)'},
             'fasta_description_newline_replacement_multi_char'),
            (newline_description_gen(),
             {'description_newline_replacement': ''},
             'fasta_description_newline_replacement_empty_str'),
            (whitespace_id_gen(),
             {'id_whitespace_replacement': '>:o'},
             'fasta_id_whitespace_replacement_multi_char'),
            (whitespace_id_gen(),
             {'id_whitespace_replacement': ''},
             'fasta_id_whitespace_replacement_empty_str')
        ])

        self.blank_seq = BiologicalSequence('')

        def blank_seq_gen():
            for seq in self.bio_seq1, self.blank_seq:
                yield seq

        # generators or parameter combos that cannot be written in fasta
        # format, paired with kwargs (if any), error type, and expected error
        # message regexp
        self.invalid_objs = [
            (blank_seq_gen(), {}, FASTAFormatError, '2nd.*empty'),
            (single_seq_gen(),
             {'max_width': 0}, ValueError, 'n=0'),
            (multi_seq_gen(), {'id_whitespace_replacement': '-\n_'},
             FASTAFormatError, 'Newline character'),
            (multi_seq_gen(), {'description_newline_replacement': '-.-\n'},
             FASTAFormatError, 'Newline character')
        ]

    # extensive tests for generator -> fasta writer since it is used by all
    # other object -> fasta writers

    def test_generator_to_fasta(self):
        for obj, kwargs, fp in self.objs_fps:
            fh = StringIO()
            _generator_to_fasta(obj, fh, **kwargs)
            obs = fh.getvalue()
            fh.close()

            with open(fp, 'U') as fh:
                exp = fh.read()

            self.assertEqual(obs, exp)

    def test_generator_to_fasta_invalid_input(self):
        for obj, kwargs, error_type, error_msg_regexp in self.invalid_objs:
            fh = StringIO()
            with self.assertRaisesRegexp(error_type, error_msg_regexp):
                _generator_to_fasta(obj, fh, **kwargs)
            fh.close()

    # light testing of object -> fasta writers to ensure interface is present
    # and kwargs are passed through. extensive testing of underlying writer is
    # performed above

    def test_any_sequence_to_fasta(self):
        # Store writer function, sequence object to write, and expected
        # filepaths for each of the invoked keyword arguments (see below).
        id_ = 'f o o'
        desc = 'b\na\nr'
        test_data = (
            (_biological_sequence_to_fasta,
             BiologicalSequence('ACGT', id=id_, description=desc),
             ('fasta_single_bio_seq_defaults',
              'fasta_single_bio_seq_non_defaults')),
            (_nucleotide_sequence_to_fasta,
             NucleotideSequence('ACGTU', id=id_, description=desc),
             ('fasta_single_nuc_seq_defaults',
              'fasta_single_nuc_seq_non_defaults')),
            (_dna_sequence_to_fasta,
             DNA('TACG', id=id_, description=desc),
             ('fasta_single_dna_seq_defaults',
              'fasta_single_dna_seq_non_defaults')),
            (_rna_sequence_to_fasta,
             RNA('UACG', id=id_, description=desc),
             ('fasta_single_rna_seq_defaults',
              'fasta_single_rna_seq_non_defaults')),
            (_protein_sequence_to_fasta,
             Protein('PQQ', id=id_, description=desc),
             ('fasta_single_prot_seq_defaults',
              'fasta_single_prot_seq_non_defaults')))

        kwargs_non_defaults = {
            'id_whitespace_replacement': '-',
            'description_newline_replacement': '_',
            'max_width': 1
        }

        for fn, obj, fps in test_data:
            for kw, fp in zip(({}, kwargs_non_defaults), fps):
                fh = StringIO()
                fn(obj, fh, **kw)
                obs = fh.getvalue()
                fh.close()

                with open(get_data_path(fp), 'U') as fh:
                    exp = fh.read()

                self.assertEqual(obs, exp)

    def test_any_sequences_to_fasta(self):
        kwargs_non_defaults = {
            'id_whitespace_replacement': '*',
            'description_newline_replacement': '+',
            'max_width': 3
        }

        for fn, obj in ((_sequence_collection_to_fasta, self.seq_coll),
                        (_alignment_to_fasta, self.align)):
            for kw, fp in (({}, 'fasta_3_seqs_defaults'),
                           (kwargs_non_defaults, 'fasta_3_seqs_non_defaults')):
                fh = StringIO()
                fn(obj, fh, **kw)
                obs = fh.getvalue()
                fh.close()

                with open(get_data_path(fp), 'U') as fh:
                    exp = fh.read()

                self.assertEqual(obs, exp)


if __name__ == '__main__':
    main()
