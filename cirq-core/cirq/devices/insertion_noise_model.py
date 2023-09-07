# Copyright 2021 The Cirq Developers
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import dataclasses
from typing import TYPE_CHECKING, Dict, List, Optional, Sequence, Any

from cirq import devices
from cirq.devices import noise_utils

if TYPE_CHECKING:
    import cirq


@dataclasses.dataclass
class InsertionNoiseModel(devices.NoiseModel):
    """Simple base noise model for inserting operations.

    Operations generated by this model for a given moment are all added into a
    single "noise moment", which is added before or after the original moment
    based on `prepend`.

    Args:
        ops_added: a map of gate types (and optionally, qubits they act on) to
            operations that should be added. If two gate types provided apply
            to a target gate, the most specific type will match; if neither
            type is more specific (e.g. A is a subtype of B, but B defines
            qubits and A does not) then the first one appearing in this dict
            will match.
        prepend: If True, put noise before affected gates. Default: False.
        require_physical_tag: whether to only apply noise to operations tagged
            with PHYSICAL_GATE_TAG.
    """

    ops_added: Dict[noise_utils.OpIdentifier, 'cirq.Operation'] = dataclasses.field(
        default_factory=dict
    )
    prepend: bool = False
    require_physical_tag: bool = True

    def noisy_moment(
        self, moment: 'cirq.Moment', system_qubits: Sequence['cirq.Qid']
    ) -> 'cirq.OP_TREE':
        noise_ops: List['cirq.Operation'] = []
        candidate_ops = [
            op
            for op in moment
            if (not self.require_physical_tag) or noise_utils.PHYSICAL_GATE_TAG in op.tags
        ]
        for op in candidate_ops:
            match_id: Optional[noise_utils.OpIdentifier] = None
            candidate_ids = [op_id for op_id in self.ops_added if op in op_id]
            for op_id in candidate_ids:
                if match_id is None or op_id.is_proper_subtype_of(match_id):
                    match_id = op_id
            if match_id is not None:
                noise_ops.append(self.ops_added[match_id])
        if not noise_ops:
            return [moment]

        from cirq import circuits

        noise_steps = circuits.Circuit(noise_ops)
        if self.prepend:
            return [*noise_steps.moments, moment]
        return [moment, *noise_steps.moments]

    def _json_dict_(self) -> Dict[str, Any]:
        return {
            'ops_added': list(self.ops_added.items()),
            'prepend': self.prepend,
            'require_physical_tag': self.require_physical_tag,
        }

    @classmethod
    def _from_json_dict_(cls, ops_added, prepend,require_physical_tag, **kwargs):
        return cls(
            ops_added=dict(ops_added), prepend=prepend, require_physical_tag=require_physical_tag
        )
