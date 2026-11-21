from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.schemas.decision import FraudDecisionCreateRequest


@pytest.mark.parametrize("reason", ["          ", "   brief   "])
def test_decision_requires_meaningful_reason(reason):
    with pytest.raises(ValidationError):
        FraudDecisionCreateRequest(case_id=uuid4(), decision="confirmed_fraud",
                                   decision_reason=reason)
