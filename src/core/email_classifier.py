"""
Email Classifier Skill - v0.4 Optional Feature
Intelligent email classification and filtering for Gmail.

Features:
    - Auto-classify incoming emails
    - Smart labeling and filtering
    - Priority detection
    - Spam/important detection
    - Custom classification rules
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple
import asyncio
import json
import re

from ..utils.logger import logger


class EmailCategory(Enum):
    """Email categories for classification."""
    PRIMARY = "primary"          # Important personal emails
    SOCIAL = "social"            # Social network notifications
    PROMOTIONS = "promotions"    # Marketing and promotional
    UPDATES = "updates"          # Bills, receipts, statements
    FORUMS = "forums"            # Mailing lists, forums
    SPAM = "spam"                # Spam/junk
    IMPORTANT = "important"      # High priority
    WORK = "work"                # Work-related
    PERSONAL = "personal"        # Personal emails
    NEWSLETTER = "newsletter"    # Newsletters
    NOTIFICATION = "notification"  # System notifications
    UNKNOWN = "unknown"


class EmailPriority(Enum):
    """Email priority levels."""
    CRITICAL = "critical"   # Needs immediate attention
    HIGH = "high"          # Important
    NORMAL = "normal"      # Regular email
    LOW = "low"           # Can wait
    ARCHIVE = "archive"    # Auto-archive


@dataclass
class EmailMessage:
    """Represents an email message."""
    id: str
    subject: str
    sender: str
    sender_name: str = ""
    recipients: List[str] = field(default_factory=list)
    body_text: str = ""
    body_html: str = ""
    received_at: datetime = field(default_factory=datetime.now)
    labels: List[str] = field(default_factory=list)
    is_read: bool = False
    has_attachments: bool = False
    attachment_count: int = 0
    thread_id: str = None
    headers: Dict[str, str] = field(default_factory=dict)
    
    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "subject": self.subject,
            "sender": self.sender,
            "sender_name": self.sender_name,
            "received_at": self.received_at.isoformat(),
            "labels": self.labels,
            "is_read": self.is_read,
            "has_attachments": self.has_attachments,
        }


@dataclass
class ClassificationResult:
    """Result of email classification."""
    email_id: str
    category: EmailCategory
    priority: EmailPriority
    confidence: float  # 0.0 to 1.0
    suggested_labels: List[str] = field(default_factory=list)
    suggested_action: str = None  # e.g., "archive", "star", "reply"
    reason: str = ""
    matched_rules: List[str] = field(default_factory=list)
    
    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "email_id": self.email_id,
            "category": self.category.value,
            "priority": self.priority.value,
            "confidence": round(self.confidence, 2),
            "suggested_labels": self.suggested_labels,
            "suggested_action": self.suggested_action,
            "reason": self.reason,
        }


@dataclass
class ClassificationRule:
    """A rule for email classification."""
    id: str
    name: str
    conditions: Dict[str, Any]  # Field -> pattern/value
    category: EmailCategory
    priority: EmailPriority = None
    labels: List[str] = field(default_factory=list)
    action: str = None
    enabled: bool = True
    
    def matches(self, email: EmailMessage) -> Tuple[bool, float]:
        """
        Check if email matches this rule.
        
        Returns (matches, confidence)
        """
        if not self.enabled:
            return False, 0.0
        
        matched_count = 0
        total_conditions = len(self.conditions)
        
        for field_name, pattern in self.conditions.items():
            value = self._get_field_value(email, field_name)
            if value and self._matches_pattern(value, pattern):
                matched_count += 1
        
        if matched_count == total_conditions:
            confidence = 1.0
        elif matched_count > 0:
            confidence = matched_count / total_conditions * 0.8
        else:
            confidence = 0.0
        
        return matched_count == total_conditions, confidence
    
    def _get_field_value(self, email: EmailMessage, field_name: str) -> Optional[str]:
        """Get field value from email."""
        field_map = {
            "subject": email.subject,
            "sender": email.sender,
            "sender_name": email.sender_name,
            "body": email.body_text,
            "domain": email.sender.split("@")[-1] if "@" in email.sender else "",
        }
        return field_map.get(field_name, "")
    
    def _matches_pattern(self, value: str, pattern: Any) -> bool:
        """Check if value matches pattern."""
        if isinstance(pattern, str):
            # Simple substring match (case insensitive)
            return pattern.lower() in value.lower()
        elif isinstance(pattern, list):
            # Match any in list
            return any(p.lower() in value.lower() for p in pattern)
        elif isinstance(pattern, dict):
            # Regex match
            if "regex" in pattern:
                return bool(re.search(pattern["regex"], value, re.IGNORECASE))
            if "exact" in pattern:
                return value.lower() == pattern["exact"].lower()
            if "starts_with" in pattern:
                return value.lower().startswith(pattern["starts_with"].lower())
            if "ends_with" in pattern:
                return value.lower().endswith(pattern["ends_with"].lower())
        return False


# Default classification rules
DEFAULT_RULES: List[ClassificationRule] = [
    # Social
    ClassificationRule(
        id="social_facebook",
        name="Facebook Notifications",
        conditions={"domain": "facebookmail.com"},
        category=EmailCategory.SOCIAL,
        labels=["social", "facebook"],
    ),
    ClassificationRule(
        id="social_twitter",
        name="Twitter/X Notifications",
        conditions={"domain": ["twitter.com", "x.com"]},
        category=EmailCategory.SOCIAL,
        labels=["social", "twitter"],
    ),
    ClassificationRule(
        id="social_linkedin",
        name="LinkedIn Notifications",
        conditions={"domain": "linkedin.com"},
        category=EmailCategory.SOCIAL,
        labels=["social", "linkedin"],
    ),
    
    # Promotions
    ClassificationRule(
        id="promo_unsubscribe",
        name="Promotional with Unsubscribe",
        conditions={"body": {"regex": r"unsubscribe|opt.?out"}},
        category=EmailCategory.PROMOTIONS,
        priority=EmailPriority.LOW,
    ),
    ClassificationRule(
        id="promo_marketing",
        name="Marketing Emails",
        conditions={"subject": ["% off", "sale", "deal", "discount", "limited time"]},
        category=EmailCategory.PROMOTIONS,
        priority=EmailPriority.LOW,
    ),
    
    # Updates
    ClassificationRule(
        id="updates_receipt",
        name="Receipts",
        conditions={"subject": ["receipt", "order confirmation", "invoice"]},
        category=EmailCategory.UPDATES,
        labels=["receipts"],
    ),
    ClassificationRule(
        id="updates_shipping",
        name="Shipping Updates",
        conditions={"subject": ["shipped", "delivered", "tracking", "out for delivery"]},
        category=EmailCategory.UPDATES,
        labels=["shipping"],
    ),
    
    # Newsletters
    ClassificationRule(
        id="newsletter_weekly",
        name="Weekly Newsletters",
        conditions={"subject": ["weekly", "newsletter", "digest"]},
        category=EmailCategory.NEWSLETTER,
        priority=EmailPriority.LOW,
    ),
    
    # Important
    ClassificationRule(
        id="important_urgent",
        name="Urgent Emails",
        conditions={"subject": ["urgent", "asap", "immediately", "action required"]},
        category=EmailCategory.IMPORTANT,
        priority=EmailPriority.CRITICAL,
        labels=["important"],
    ),
    
    # Notifications
    ClassificationRule(
        id="notification_github",
        name="GitHub Notifications",
        conditions={"domain": "github.com"},
        category=EmailCategory.NOTIFICATION,
        labels=["github", "dev"],
    ),
    ClassificationRule(
        id="notification_google",
        name="Google Notifications",
        conditions={"domain": ["google.com", "accounts.google.com"]},
        category=EmailCategory.NOTIFICATION,
        labels=["google"],
    ),
]


class EmailClassifier:
    """
    Email classification engine.
    
    Usage:
        classifier = get_email_classifier()
        
        # Classify single email
        result = classifier.classify(email)
        
        # Batch classify
        results = classifier.classify_batch(emails)
        
        # Add custom rule
        classifier.add_rule(rule)
    """
    
    _instance: Optional["EmailClassifier"] = None
    
    def __init__(self):
        self._rules: List[ClassificationRule] = DEFAULT_RULES.copy()
        self._user_rules: Dict[str, List[ClassificationRule]] = {}
        self._llm_enabled = False
        self._data_path = "data/email_classifier.json"
        self._load_rules()
    
    def _load_rules(self):
        """Load custom rules from disk."""
        try:
            import os
            if os.path.exists(self._data_path):
                with open(self._data_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for user_id, rules_data in data.get("user_rules", {}).items():
                        self._user_rules[user_id] = [
                            ClassificationRule(
                                id=r["id"],
                                name=r["name"],
                                conditions=r["conditions"],
                                category=EmailCategory(r["category"]),
                                priority=EmailPriority(r["priority"]) if r.get("priority") else None,
                                labels=r.get("labels", []),
                                action=r.get("action"),
                                enabled=r.get("enabled", True),
                            )
                            for r in rules_data
                        ]
        except Exception as e:
            logger.warning(f"Failed to load email classifier rules: {e}")
    
    def _save_rules(self):
        """Save custom rules to disk."""
        try:
            import os
            os.makedirs(os.path.dirname(self._data_path), exist_ok=True)
            
            data = {
                "user_rules": {
                    user_id: [
                        {
                            "id": r.id,
                            "name": r.name,
                            "conditions": r.conditions,
                            "category": r.category.value,
                            "priority": r.priority.value if r.priority else None,
                            "labels": r.labels,
                            "action": r.action,
                            "enabled": r.enabled,
                        }
                        for r in rules
                    ]
                    for user_id, rules in self._user_rules.items()
                }
            }
            
            with open(self._data_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.warning(f"Failed to save email classifier rules: {e}")
    
    def classify(
        self,
        email: EmailMessage,
        user_id: str = None,
    ) -> ClassificationResult:
        """
        Classify a single email.
        
        Args:
            email: Email to classify
            user_id: User ID for custom rules
        """
        # Get applicable rules
        rules = self._rules.copy()
        if user_id and user_id in self._user_rules:
            rules = self._user_rules[user_id] + rules
        
        best_match: Optional[ClassificationRule] = None
        best_confidence = 0.0
        matched_rules = []
        
        # Try each rule
        for rule in rules:
            matches, confidence = rule.matches(email)
            if matches and confidence > best_confidence:
                best_match = rule
                best_confidence = confidence
            if matches:
                matched_rules.append(rule.name)
        
        if best_match:
            return ClassificationResult(
                email_id=email.id,
                category=best_match.category,
                priority=best_match.priority or self._infer_priority(email),
                confidence=best_confidence,
                suggested_labels=best_match.labels,
                suggested_action=best_match.action,
                reason=f"Matched rule: {best_match.name}",
                matched_rules=matched_rules,
            )
        
        # Fallback to heuristic classification
        return self._classify_heuristic(email)
    
    def _classify_heuristic(self, email: EmailMessage) -> ClassificationResult:
        """Heuristic classification when no rules match."""
        subject_lower = email.subject.lower()
        sender_lower = email.sender.lower()
        body_lower = email.body_text.lower()[:1000]  # First 1000 chars
        
        category = EmailCategory.PRIMARY
        priority = EmailPriority.NORMAL
        labels = []
        confidence = 0.5
        
        # Check for spam indicators
        spam_indicators = ["winner", "lottery", "claim your prize", "viagra", "crypto"]
        if any(ind in subject_lower or ind in body_lower for ind in spam_indicators):
            category = EmailCategory.SPAM
            priority = EmailPriority.ARCHIVE
            confidence = 0.7
        
        # Check for notifications
        elif "noreply" in sender_lower or "no-reply" in sender_lower:
            category = EmailCategory.NOTIFICATION
            priority = EmailPriority.LOW
            confidence = 0.6
        
        # Check for work-related
        elif any(word in subject_lower for word in ["meeting", "schedule", "project", "deadline"]):
            category = EmailCategory.WORK
            priority = EmailPriority.HIGH
            confidence = 0.6
            labels.append("work")
        
        return ClassificationResult(
            email_id=email.id,
            category=category,
            priority=priority,
            confidence=confidence,
            suggested_labels=labels,
            reason="Heuristic classification",
        )
    
    def _infer_priority(self, email: EmailMessage) -> EmailPriority:
        """Infer priority from email content."""
        subject_lower = email.subject.lower()
        
        if any(word in subject_lower for word in ["urgent", "asap", "immediate", "critical"]):
            return EmailPriority.CRITICAL
        elif any(word in subject_lower for word in ["important", "action required", "deadline"]):
            return EmailPriority.HIGH
        elif any(word in subject_lower for word in ["fyi", "newsletter", "digest"]):
            return EmailPriority.LOW
        
        return EmailPriority.NORMAL
    
    def classify_batch(
        self,
        emails: List[EmailMessage],
        user_id: str = None,
    ) -> List[ClassificationResult]:
        """Classify multiple emails."""
        return [self.classify(email, user_id) for email in emails]
    
    def add_rule(
        self,
        user_id: str,
        rule_id: str,
        name: str,
        conditions: Dict[str, Any],
        category: EmailCategory,
        priority: EmailPriority = None,
        labels: List[str] = None,
        action: str = None,
    ) -> ClassificationRule:
        """Add a custom rule for a user."""
        rule = ClassificationRule(
            id=rule_id,
            name=name,
            conditions=conditions,
            category=category,
            priority=priority,
            labels=labels or [],
            action=action,
        )
        
        if user_id not in self._user_rules:
            self._user_rules[user_id] = []
        
        # Remove existing rule with same ID
        self._user_rules[user_id] = [r for r in self._user_rules[user_id] if r.id != rule_id]
        self._user_rules[user_id].append(rule)
        
        self._save_rules()
        return rule
    
    def remove_rule(self, user_id: str, rule_id: str) -> bool:
        """Remove a custom rule."""
        if user_id not in self._user_rules:
            return False
        
        original_count = len(self._user_rules[user_id])
        self._user_rules[user_id] = [r for r in self._user_rules[user_id] if r.id != rule_id]
        
        if len(self._user_rules[user_id]) < original_count:
            self._save_rules()
            return True
        return False
    
    def get_user_rules(self, user_id: str) -> List[ClassificationRule]:
        """Get custom rules for a user."""
        return self._user_rules.get(user_id, [])
    
    def get_all_rules(self, user_id: str = None) -> List[ClassificationRule]:
        """Get all applicable rules."""
        rules = self._rules.copy()
        if user_id and user_id in self._user_rules:
            rules = self._user_rules[user_id] + rules
        return rules
    
    def get_status_message(self, user_id: str) -> str:
        """Get formatted status message."""
        user_rules = self.get_user_rules(user_id)
        total_rules = len(self._rules) + len(user_rules)
        
        lines = [
            "📧 **Email Classifier**",
            "",
            f"Total Rules: {total_rules}",
            f"System Rules: {len(self._rules)}",
            f"Custom Rules: {len(user_rules)}",
            "",
        ]
        
        if user_rules:
            lines.append("**Your Custom Rules:**")
            for rule in user_rules[:5]:
                status = "✓" if rule.enabled else "✗"
                lines.append(f"{status} {rule.name} → {rule.category.value}")
        
        lines.extend([
            "",
            "**Categories:**",
        ])
        for cat in EmailCategory:
            if cat != EmailCategory.UNKNOWN:
                lines.append(f"• {cat.value}")
        
        lines.extend([
            "",
            "**Commands:**",
            "/email rules - List all rules",
            "/email add <name> <condition> <category> - Add rule",
            "/email remove <rule_id> - Remove rule",
            "/email test <email_json> - Test classification",
        ])
        
        return "\n".join(lines)


# Singleton instance
_email_classifier: Optional[EmailClassifier] = None


def get_email_classifier() -> EmailClassifier:
    """Get the global email classifier instance."""
    global _email_classifier
    if _email_classifier is None:
        _email_classifier = EmailClassifier()
    return _email_classifier


def reset_email_classifier():
    """Reset the classifier (for testing)."""
    global _email_classifier
    _email_classifier = None


__all__ = [
    "EmailCategory",
    "EmailPriority",
    "EmailMessage",
    "ClassificationResult",
    "ClassificationRule",
    "DEFAULT_RULES",
    "EmailClassifier",
    "get_email_classifier",
    "reset_email_classifier",
]
