"""Test for File classes"""

from copy import deepcopy
import itertools


import pytest
import numpy as np

import label


@pytest.fixture()
def zstack_edit(zstack_project):
    return label.ZStackEdit(zstack_project)


@pytest.fixture
def track_edit(track_project):
    return label.TrackEdit(track_project)


@pytest.fixture
def change_display(project):
    return label.ChangeDisplay(project)


@pytest.fixture(params=[
    pytest.lazy_fixture('zstack_edit'),
    pytest.lazy_fixture('track_edit')
])
def edit(request):
    return request.param

# Tests can mock a series of actions on different frames/features/channels
# by manually setting edit.project.frame/feature/channel within the test

# Tests for EditView


def test_change_channel(change_display):
    for channel in range(change_display.num_channels):
        change_display.change('channel', channel)
        assert change_display.project.channel == channel
    with pytest.raises(ValueError):
        change_display.change('channel', -1)
    with pytest.raises(ValueError):
        change_display.change('channel', change_display.num_channels)


def test_change_feature(change_display):
    for feature in range(change_display.num_features):
        change_display.change('feature', feature)
        assert change_display.project.feature == feature
    with pytest.raises(ValueError):
        change_display.change('feature', -1)
    with pytest.raises(ValueError):
        change_display.change('feature', change_display.num_features)


def test_change_frame(change_display):
    for frame in range(change_display.num_frames):
        change_display.change('frame', frame)
        assert change_display.project.frame == frame
    with pytest.raises(ValueError):
        change_display.change('frame', -1)
    with pytest.raises(ValueError):
        change_display.change('frame', change_display.num_frames)


# Tests for Edit


def test_zstack_add_cell_info(zstack_edit):
    num_frames = zstack_edit.project.num_frames
    cell_ids = zstack_edit.labels.cell_ids
    cell_info = zstack_edit.labels.cell_info
    assert not zstack_edit.y_changed
    assert not zstack_edit.labels_changed
    for feature in cell_ids:
        new_label = cell_ids[feature].max() + 1 if len(cell_ids[feature]) != 0 else 1
        assert new_label not in cell_ids[feature]
        zstack_edit.project.feature = feature
        # Add new label to first frame
        zstack_edit.add_cell_info(new_label, 0)
        assert new_label in cell_ids[feature]
        assert cell_info[feature][new_label] == {'label': str(new_label),
                                                 'frames': [0],
                                                 'slices': ''}
        assert zstack_edit.y_changed
        assert zstack_edit.labels_changed
        # Add new label to all frames (including first frame again)
        for frame in range(num_frames):
            assert new_label in cell_ids[feature]
            zstack_edit.add_cell_info(new_label, frame)
            assert cell_info[feature][new_label] == {'label': str(new_label),
                                                     'frames': list(range(frame + 1)),
                                                     'slices': ''}
            assert zstack_edit.y_changed
            assert zstack_edit.labels_changed


def test_track_add_cell_info(track_edit):
    num_frames = track_edit.project.num_frames
    tracks = track_edit.labels.tracks
    new_label = max(tracks) + 1 if len(tracks) != 0 else 1
    assert not track_edit.y_changed
    assert not track_edit.labels_changed
    assert new_label not in tracks
    # Add new label to first frame
    track_edit.add_cell_info(new_label, 0)
    assert tracks[new_label] == {
        'label': int(new_label),
        'frames': [0],
        'daughters': [],
        'frame_div': None,
        'parent': None,
        'capped': False,
    }
    assert track_edit.y_changed
    assert track_edit.labels_changed
    # Add new label to all frames (including first frame again)
    for frame in range(num_frames):
        track_edit.add_cell_info(new_label, frame)
        assert tracks[new_label] == {
            'label': int(new_label),
            'frames': list(range(frame + 1)),
            'daughters': [],
            'frame_div': None,
            'parent': None,
            'capped': False,
        }
        assert track_edit.y_changed
        assert track_edit.labels_changed


def test_del_cell_info(edit):
    num_frames = edit.project.num_frames
    cell_ids = edit.labels.cell_ids
    cell_info = edit.labels.cell_info
    assert not edit.y_changed
    assert not edit.labels_changed
    for feature in cell_ids:
        edit.project.feature = feature
        for cell in cell_ids[feature]:
            assert cell in cell_ids[feature]
            assert cell in cell_info[feature]
            # Remove from all frames except last
            for frame in range(num_frames - 1):
                edit.del_cell_info(cell, frame)
                assert frame not in cell_info[feature][cell]['frames']
                assert edit.y_changed
                assert edit.labels_changed
            # Remove frm last frame
            assert cell in cell_ids[feature]
            assert cell in cell_info[feature]
            edit.del_cell_info(cell, num_frames - 1)
            assert cell not in cell_ids[feature]
            assert cell not in cell_info[feature]
            assert edit.y_changed
            assert edit.labels_changed
        # All cells removed from feature
        np.testing.assert_array_equal(cell_ids[feature], np.array([]))
        assert edit.labels.cell_info[feature] == {}


def test_action_new_single_cell(edit):
    num_frames = edit.project.num_frames
    cell_ids = deepcopy(edit.labels.cell_ids)
    for feature in cell_ids:
        edit.project.feature = feature
        for cell in cell_ids[feature]:
            # Replace cell in all frames but last
            for frame in range(num_frames - 1):
                edit.project.frame = frame
                edit.action_new_single_cell(cell)
                new_label = edit.project.get_max_label()
                # TODO: @tddough98 this assert assumes that cell is present in every frame
                assert new_label in edit.project.label_array[frame, ..., feature]
                assert cell not in edit.project.label_array[frame, ..., feature]
            # Replace cell in last frame
            edit.project.frame = num_frames - 1
            edit.action_new_single_cell(cell)
            new_label = edit.project.get_max_label()
            # TODO: @tddough98 this assert assumes that cell is present in every frame
            assert new_label in edit.project.label_array[num_frames - 1]
            assert cell not in edit.project.label_array[..., feature]


def test_action_delete_mask(edit):
    num_frames = edit.project.num_frames
    cell_ids = deepcopy(edit.labels.cell_ids)
    for feature in cell_ids:
        edit.project.feature = feature
        for cell in cell_ids[feature]:
            for frame in range(num_frames - 1):
                edit.project.frame = frame
                edit.action_delete_mask(cell)
                assert cell not in edit.project.label_array[frame, ..., feature]
            edit.project.frame = num_frames - 1
            edit.action_delete_mask(cell)
            assert cell not in edit.project.label_array[..., feature]


def test_action_swap_single_frame(edit):
    num_frames = edit.project.num_frames
    cell_ids = deepcopy(edit.labels.cell_ids)
    assert not edit.y_changed
    assert not edit.labels_changed
    for feature in cell_ids:
        edit.project.feature = feature
        # All pairs of labels in that feature
        for cell1, cell2 in itertools.product(cell_ids[feature], cell_ids[feature]):
            for frame in range(num_frames):
                edit.project.frame = frame
                cell1_ann = edit.frame[..., feature] == cell1
                cell2_ann = edit.frame[..., feature] == cell2
                edit.action_swap_single_frame(cell1, cell2)
                np.testing.assert_array_equal(cell1_ann, edit.frame[..., feature] == cell2)
                np.testing.assert_array_equal(cell2_ann, edit.frame[..., feature] == cell1)
                assert edit.y_changed
                assert edit.labels_changed

# def test_action_handle_draw(edit):

#     for feature in cell_ids:
#         edit.project.feature = feature

#     self, trace, target_value, brush_value, brush_size, erase, frame):
#     """Use a "brush" to draw in the brush value along trace locations of
#         the annotated data.
#     """

# def test_action_trim_pixels(edit):
#     max_frames = edit.file.max_frames
#     ann = edit.annotated
#     cell_ids = deepcopy(edit.file.cell_ids)
#     assert not edit._y_changed
#     assert not edit.labels_changed
#     for feature in cell_ids:
#         edit.project.feature = feature
#         for cell in cell_ids[feature]:
#             for frame in range(max_frames):
#                 edit.action_trim_pixels(cell, frame, x_location, y_location)

#             (self, label, frame, x_location, y_location)


# def test_action_fill_hole(edit):

#     edit.action_fill_hole(label, frame, x_location, y_location)

#     pass


# def test_action_flood_contiguous(edit):

#     edit.action_flood_contiguous(label, frame, x_location, y_location)

# def test_action_watershed(edit):

#     edit.action_watershed(label, frame, x1_location, y1_location, x2_location, y2_location)

# def test_action_threshold(edit):

#     edit.action_threshold(y1, x1, y2, x2, frame, label):


# Tests for zstack specific actions

def test_action_new_cell_stack(zstack_edit):
    for feature in range(zstack_edit.project.num_features):
        zstack_edit.project.feature = feature
        label = zstack_edit.project.get_max_label()
        if label == 0:  # no labels in feature
            continue
        frames = zstack_edit.labels.cell_info[feature][label]['frames']
        # replace from back to front
        for frame in frames[::-1]:
            zstack_edit.project.frame = frame
            new_label = zstack_edit.project.get_max_label() + 1
            zstack_edit.action_new_cell_stack(label)
            # TODO: this assert assumes that label was in every frame
            assert new_label in zstack_edit.project.label_array[frame, ..., feature]
            assert label not in zstack_edit.project.label_array[frame:, ..., feature]
        # replace only in first frame
        label = zstack_edit.project.get_max_label()
        new_label = label + 1
        frames = zstack_edit.labels.cell_info[feature][label]['frames']
        zstack_edit.project.frame = frames[0]
        zstack_edit.action_new_cell_stack(label)
        assert label not in zstack_edit.project.label_array[..., feature]
        for frame in frames:
            # TODO: this assert assumes that label is in every frame
            zstack_edit.project.frame = frame
            assert new_label in zstack_edit.frame[..., feature]


def test_action_replace_single(zstack_edit):
    for feature in range(zstack_edit.project.num_features):
        zstack_edit.project.feature = feature
        labels = zstack_edit.labels.cell_ids[feature]
        for cell1, cell2 in itertools.product(labels, labels):
            # Front end checks labels are different
            # TODO: check on backend and make tests for the check
            if cell1 == cell2:
                continue
            for frame in range(zstack_edit.project.num_frames):
                annotated = zstack_edit.project.label_array[frame, ..., feature].copy()
                # Front end checks labels selected in the same frame
                # TODO: check on backend and make tests for the check
                if (cell1 not in annotated or cell2 not in annotated):
                    continue
                assert cell1 in annotated
                assert cell2 in annotated
                zstack_edit.project.frame = frame
                zstack_edit.action_replace_single(cell1, cell2)
                new_ann = zstack_edit.project.label_array[frame, ..., feature]
                assert cell1 in new_ann
                assert cell2 not in new_ann
                assert ((new_ann == cell1) == ((annotated == cell1) | (annotated == cell2))).all()


def test_action_replace(zstack_edit):
    for feature in range(zstack_edit.project.num_features):
        zstack_edit.project.feature = feature
        labels = zstack_edit.labels.cell_ids[feature]
        for cell1, cell2 in itertools.product(labels, labels):
            old_ann = zstack_edit.project.label_array[..., feature].copy()
            # Front end checks labels are different
            # TODO: check on backend and make tests for these checks
            if cell1 == cell2:
                continue
            zstack_edit.action_replace(cell1, cell2)
            ann = zstack_edit.project.label_array[..., feature]
            assert cell1 in ann
            assert cell2 not in ann
            assert (ann[old_ann == cell2] == cell1).all()


def test_action_swap_all_frame(zstack_edit):
    for feature in range(zstack_edit.project.num_features):
        zstack_edit.project.feature = feature
        labels = zstack_edit.labels.cell_ids[feature]
        for cell1, cell2 in itertools.product(labels, labels):
            old_ann = zstack_edit.project.label_array[..., feature].copy()
            old_cell_info = zstack_edit.labels.cell_info.copy()
            zstack_edit.action_swap_all_frame(cell1, cell2)
            ann = zstack_edit.project.label_array[..., feature]
            cell_info = zstack_edit.labels.cell_info
            assert (ann[old_ann == cell1] == cell2).all()
            assert (ann[old_ann == cell2] == cell1).all()
            assert old_cell_info[feature][cell1]['frames'] == cell_info[feature][cell2]['frames']
            assert old_cell_info[feature][cell2]['frames'] == cell_info[feature][cell1]['frames']


# Tests for TrackEdit specific actions

def test_action_new_track(track_edit):
    for label in track_edit.labels.cell_ids[0]:
        track = track_edit.labels.tracks[label].copy()
        # New track on first frame of the track has no effect
        track_edit.project.frame = track['frames'][0]
        track_edit.action_new_track(label)
        assert track == track_edit.labels.tracks[label]
        # New track on other frames replaces label on all following frames
        for frame in track['frames'][1:]:
            track_edit.project.frame = frame
            new_label = track_edit.project.get_max_label() + 1
            track_edit.action_new_track(label)
            assert new_label in track_edit.labels.cell_ids[0]
            assert track['frames'] == (track_edit.labels.tracks[label]['frames'] +
                                       track_edit.labels.tracks[new_label]['frames'])
            # Only create a one new track
            break
