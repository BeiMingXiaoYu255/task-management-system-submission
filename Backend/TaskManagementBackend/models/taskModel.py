"""任务、任务分配（待办）、任务审核记录 ORM 模型。"""

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import relationship

from TaskManagementBackend.models.baseModel import Base, TimestampMixin, createEnumColumn
from TaskManagementBackend.models.enums import (
    AcceptanceMode,
    AssignmentMode,
    AssignmentStatus,
    ReviewResult,
    TaskPriority,
    TaskStatus,
)


class Task(Base, TimestampMixin):
    """任务实体：由有权限的成员发布，可分派给指定成员或某个级别范围。

    聚合状态说明：任务状态由服务层根据全部待办状态重算，
    便于列表页直接按任务状态筛选。
    """

    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True, autoincrement=True, comment="Task primary key")
    teamId = Column("team_id", Integer, ForeignKey("teams.id", ondelete="CASCADE"), nullable=False, comment="Team")
    title = Column(String(200), nullable=False, comment="Task title")
    description = Column(Text, nullable=True, comment="Task description")
    priority = Column(
        "priority", createEnumColumn(TaskPriority, "task_priority"), nullable=False, default=TaskPriority.MEDIUM
    )
    status = Column(
        "status", createEnumColumn(TaskStatus, "task_status"), nullable=False, default=TaskStatus.PUBLISHED
    )
    assignmentMode = Column(
        "assignment_mode", createEnumColumn(AssignmentMode, "assignment_mode"), nullable=False
    )
    acceptanceMode = Column(
        "acceptance_mode", createEnumColumn(AcceptanceMode, "acceptance_mode"), nullable=False,
        default=AcceptanceMode.MANDATORY,
    )
    targetLevelMin = Column("target_level_min", Integer, nullable=True, comment="Minimum level for level range mode")
    targetLevelMax = Column("target_level_max", Integer, nullable=True, comment="Maximum level for level range mode")
    dueAt = Column("due_at", DateTime, nullable=True, comment="Due date")
    createdBy = Column(
        "created_by", Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, comment="Publisher"
    )
    archivedAt = Column("archived_at", DateTime, nullable=True, comment="Archived at")
    # ===== v1.1 协作与 AI 扩展字段 =====
    subTeamId = Column(
        "sub_team_id", Integer, ForeignKey("sub_teams.id", ondelete="SET NULL"), nullable=True, comment="Sub-team"
    )
    sourceTeamId = Column(
        "source_team_id", Integer, ForeignKey("teams.id", ondelete="SET NULL"), nullable=True, comment="Initiating team of the collaboration task"
    )
    sourceSubTeamId = Column(
        "source_sub_team_id", Integer, ForeignKey("sub_teams.id", ondelete="SET NULL"), nullable=True, comment="Initiating sub-team of the collaboration task"
    )
    targetTeamId = Column(
        "target_team_id", Integer, ForeignKey("teams.id", ondelete="SET NULL"), nullable=True, comment="Receiving team of the collaboration task"
    )
    targetSubTeamId = Column(
        "target_sub_team_id", Integer, ForeignKey("sub_teams.id", ondelete="SET NULL"), nullable=True, comment="Receiving sub-team of the collaboration task"
    )
    collaborationId = Column(
        "collaboration_id",
        Integer,
        ForeignKey("team_collaborations.id", ondelete="SET NULL"),
        nullable=True,
        comment="Related collaboration",
    )
    collaborationPhase = Column("collaboration_phase", String(32), nullable=True, comment="Collaboration task phase")
    collaborationComment = Column("collaboration_comment", Text, nullable=True, comment="Receiver confirmation comment")
    autoAssigned = Column("auto_assigned", Boolean, nullable=False, default=False, comment="AI auto-assigned")
    requiredSkillNames = Column(
        "required_skill_names", Text, nullable=True, comment="Required skill tags for AI assignment (lowercase, comma-separated)"
    )

    team = relationship("Team", back_populates="tasks", foreign_keys=[teamId])
    subTeam = relationship("SubTeam", foreign_keys=[subTeamId])
    sourceTeam = relationship("Team", foreign_keys=[sourceTeamId])
    targetTeam = relationship("Team", foreign_keys=[targetTeamId])
    sourceSubTeam = relationship("SubTeam", foreign_keys=[sourceSubTeamId])
    targetSubTeam = relationship("SubTeam", foreign_keys=[targetSubTeamId])
    collaboration = relationship("TeamCollaboration", back_populates="tasks", foreign_keys=[collaborationId])
    creator = relationship("User", back_populates="createdTasks", foreign_keys=[createdBy])
    assignments = relationship(
        "TaskAssignment", back_populates="task", cascade="all, delete-orphan", lazy="selectin"
    )
    reviews = relationship(
        "TaskReview", back_populates="task", cascade="all, delete-orphan", order_by="TaskReview.createdAt.desc()"
    )

    def __repr__(self) -> str:
        """调试输出：任务主键、标题与状态。"""
        return f"<Task id={self.id} title={self.title} status={self.status}>"


class TaskAssignment(Base, TimestampMixin):
    """任务分配记录：即执行人的个人待办，承载个人进度与审核意见。"""

    __tablename__ = "task_assignments"
    __table_args__ = (UniqueConstraint("task_id", "user_id", name="uk_task_user"),)

    id = Column(Integer, primary_key=True, autoincrement=True, comment="Primary key")
    taskId = Column("task_id", Integer, ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False, comment="Task")
    userId = Column("user_id", Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, comment="Assignee")
    status = Column(
        "status",
        createEnumColumn(AssignmentStatus, "assignment_status"),
        nullable=False,
        default=AssignmentStatus.PENDING_ACCEPTANCE,
    )
    acceptedAt = Column("accepted_at", DateTime, nullable=True, comment="Accepted/auto-accepted time")
    submittedAt = Column("submitted_at", DateTime, nullable=True, comment="Submitted time")
    reviewedAt = Column("reviewed_at", DateTime, nullable=True, comment="Review time")
    reviewedBy = Column(
        "reviewed_by", Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, comment="Reviewer"
    )
    reviewComment = Column("review_comment", Text, nullable=True, comment="Latest review comment")
    # ===== v1.1 双审核与分配来源扩展字段 =====
    reviewStage = Column("review_stage", String(16), nullable=True, comment="Two-stage review phase: target/source")
    targetReviewedAt = Column("target_reviewed_at", DateTime, nullable=True, comment="Receiver liaison review time")
    targetReviewerId = Column(
        "target_reviewer_id", Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, comment="Receiver reviewer"
    )
    targetReviewComment = Column("target_review_comment", Text, nullable=True, comment="Receiver review comment")
    assignmentSource = Column(
        "assignment_source", String(16), nullable=False, default="manual", comment="Assignment source: manual/ai/collaboration"
    )

    task = relationship("Task", back_populates="assignments")
    user = relationship("User", foreign_keys=[userId])
    reviewer = relationship("User", foreign_keys=[reviewedBy])
    targetReviewer = relationship("User", foreign_keys=[targetReviewerId])

    def __repr__(self) -> str:
        """调试输出：任务与执行人。"""
        return f"<TaskAssignment task={self.taskId} user={self.userId} status={self.status}>"


class TaskReview(Base):
    """任务审核记录：每次通过/驳回都留痕，用于任务详情展示审核历史。"""

    __tablename__ = "task_reviews"

    id = Column(Integer, primary_key=True, autoincrement=True, comment="Primary key")
    taskId = Column("task_id", Integer, ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False, comment="Task")
    assignmentId = Column(
        "assignment_id", Integer, ForeignKey("task_assignments.id", ondelete="CASCADE"), nullable=False, comment="To-do"
    )
    reviewerId = Column(
        "reviewer_id", Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, comment="Reviewer"
    )
    result = Column("result", createEnumColumn(ReviewResult, "review_result"), nullable=False, comment="Review result")
    comment = Column(Text, nullable=True, comment="Review comment")
    createdAt = Column("created_at", DateTime, nullable=False, comment="Review time")

    task = relationship("Task", back_populates="reviews")
    assignment = relationship("TaskAssignment")
    reviewer = relationship("User", foreign_keys=[reviewerId])

    @property
    def reviewerName(self) -> str:
        """审核人昵称：审核人可能已注销，缺省显示系统。"""
        if self.reviewer is None:
            return "System"
        return self.reviewer.nickname
