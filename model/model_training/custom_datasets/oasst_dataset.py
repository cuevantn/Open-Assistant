import gzip
import json
from pathlib import Path
from typing import Callable, Optional

import pydantic
from custom_datasets.formatting import format_pair
from oasst_shared.schemas.export import ExportMessageNode, ExportMessageTree
from torch.utils.data import Dataset


def _visit_messages_depth_first(
    node: ExportMessageNode,
    visitor: Callable[[ExportMessageNode, list[ExportMessageNode]], None],
    predicate: Optional[Callable[[ExportMessageNode, list[ExportMessageNode]], bool]] = None,
    parents: list[ExportMessageNode] = None,
):
    parents = parents or []
    if not node or predicate is not None and not predicate(node, parents):
        return
    visitor(node, parents.copy())
    if node.replies:
        parents = parents + [node]
        for c in node.replies:
            _visit_messages_depth_first(node=c, visitor=visitor, predicate=predicate, parents=parents)


def _visit_assistant_leaves(
    node: ExportMessageNode, visitor: Callable[[ExportMessageNode, list[ExportMessageNode]], None]
):
    def is_assistant_leave(node: ExportMessageNode, parents: list[ExportMessageNode]):
        return node.role == "assistant" and not node.replies

    _visit_messages_depth_first(node=node, visitor=visitor, predicate=is_assistant_leave)


class OasstDataset(Dataset):
    # splits = OrderedDict(sft=0.25, reward_model=0.4, rl=0.35)  # fractions per task

    def __init__(
        self,
        input_file_path: str | Path,
        lang: str = "en",
        top_k: Optional[int] = None,
    ) -> None:
        super().__init__()

        lang_codes = lang.split(",")

        if isinstance(input_file_path, str):
            input_file_path = Path(input_file_path)

        if input_file_path.suffix == ".gz":
            file_in = gzip.open(str(input_file_path), mode="tr", encoding="UTF-8")
        else:
            file_in = input_file_path.open("r", encoding="UTF-8")

        i = 0
        with file_in:
            # read one message tree per line
            for line in file_in:
                dict_tree = json.loads(line)

                # validate data
                tree: ExportMessageTree = pydantic.parse_obj_as(ExportMessageTree, dict_tree)

                if (
                    tree.tree_state != "ready_for_export"
                    or not tree.prompt.review_result
                    or tree.prompt.lang not in lang_codes
                ):
                    continue

                # identify all assistant leaf-nodes
                tree.prompt
                print(tree.message_tree_id, tree.tree_state)
                i += 1

        """
        total_prob = reduce(lambda prev, split: prev + split[1], self.splits.items(), 0)
        assert math.isclose(total_prob, 1), "Make sure OAPrivate split ratios add to 1"

        self.mode = split

        jsonl_file = os.path.join(data_path, file)

        with open(jsonl_file, "r", encoding="utf-8") as f:
            lines = f.readlines()

        # take a subset of the dataset based on the split
        rng = np.random.default_rng(seed=0)
        indices = np.arange(len(lines)).astype(int)
        rng.shuffle(indices)

        cumsums = np.cumsum([[0] + list(self.splits.values())])
        split_index = list(self.splits.keys()).index(split)

        start_index, end_index = int(cumsums[split_index] * len(lines)), int(cumsums[split_index + 1] * len(lines))

        self.data = [json.loads(lines[index].strip()) for index in indices[start_index:end_index]]
        """

    def __len__(self):
        return len(self.data)


if __name__ == "__main__":
    print(format_pair(("q1", "a1", "q2", "a2")))
    # x = OasstDataset("/home/koepf/LAION/exports/2023-02-19_oasst_ready_with_spam_deleted.jsonl.gz")
