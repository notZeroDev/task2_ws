#!/usr/bin/env python3

import time
import threading

import rclpy
from rclpy.node import Node
from rclpy.action import ActionServer, ActionClient, CancelResponse, GoalResponse
from rclpy.executors import MultiThreadedExecutor
from rclpy.callback_groups import ReentrantCallbackGroup

from smart_surveillance_interfaces.msg import SecurityEvent, SecurityAlert
from smart_surveillance_interfaces.action import SecurityAction


class SecurityResponseNode(Node):
    def __init__(self):
        super().__init__('security_response_node')

        # ReentrantCallbackGroup allows the action server execute_callback
        # and the subscriber callback to run concurrently without deadlocking
        self._reentrant = ReentrantCallbackGroup()

        # Parameter
        self.declare_parameter('alert_level', 2)
        self.alert_level = self.get_parameter('alert_level').value

        # Subscriber
        self.create_subscription(
            SecurityEvent,
            '/security_event',
            self.event_callback,
            10,
            callback_group=self._reentrant,
        )

        # Publisher
        self.alert_pub = self.create_publisher(SecurityAlert, '/security_alert', 10)

        # Action server
        self._action_server = ActionServer(
            self,
            SecurityAction,
            '/security_action',
            execute_callback=self.execute_callback,
            goal_callback=self.goal_callback,
            cancel_callback=self.cancel_callback,
            callback_group=self._reentrant,
        )

        # Action client — created once, reused for all goals
        self._action_client = ActionClient(
            self,
            SecurityAction,
            '/security_action',
            callback_group=self._reentrant,
        )

        self.get_logger().info(
            f'Security Response Node started  (alert_level={self.alert_level})'
        )

    # ------------------------------------------------------------------ #

    def event_callback(self, evt: SecurityEvent):
        if evt.severity < self.alert_level:
            return

        # Publish instant alert
        alert = SecurityAlert()
        alert.header = evt.header
        alert.alert_level = self.alert_level
        alert.triggered_by = evt.event_type
        alert.alert_message = (
            f'ALERT: {evt.event_type} | '
            f'object={evt.object_label} | '
            f'depth={evt.object_depth:.2f} | '
            f'severity={evt.severity}'
        )
        self.alert_pub.publish(alert)
        self.get_logger().warn(alert.alert_message)

        # Send action goal in a daemon thread — avoids blocking the executor
        thread = threading.Thread(
            target=self._send_action_goal,
            args=(evt.event_type, evt.severity),
            daemon=True,
        )
        thread.start()

    # ------------------------------------------------------------------ #

    def goal_callback(self, goal_request):
        self.get_logger().info(
            f'Action goal received: {goal_request.event_type}')
        return GoalResponse.ACCEPT

    def cancel_callback(self, goal_handle):
        self.get_logger().info('Action cancel requested')
        return CancelResponse.ACCEPT

    async def execute_callback(self, goal_handle):
        self.get_logger().info(
            f'Executing action: {goal_handle.request.event_type}')

        steps = [
            'Verifying threat...',
            'Logging incident...',
            'Notifying security personnel...',
            'Response complete.',
        ]
        feedback_msg = SecurityAction.Feedback()

        for idx, step in enumerate(steps):
            if goal_handle.is_cancel_requested:
                goal_handle.canceled()
                self.get_logger().info('Action cancelled')
                return SecurityAction.Result(success=False, summary='Cancelled')

            feedback_msg.status_message = step
            feedback_msg.progress = float(idx + 1) / len(steps)
            goal_handle.publish_feedback(feedback_msg)
            self.get_logger().info(f'[ACTION] {step}')
            time.sleep(1.0)

        goal_handle.succeed()
        result = SecurityAction.Result()
        result.success = True
        result.summary = f'Response completed for: {goal_handle.request.event_type}'
        return result

    # ------------------------------------------------------------------ #

    def _send_action_goal(self, event_type: str, severity: int):
        """Send goal from a background thread using the persistent client."""
        if not self._action_client.wait_for_server(timeout_sec=3.0):
            self.get_logger().error('Action server not available')
            return

        goal = SecurityAction.Goal()
        goal.event_type = event_type
        goal.severity = severity

        # send_goal — non-blocking future; we wait in this thread only
        future = self._action_client.send_goal_async(goal)
        # Spin the future from this thread without touching the main executor
        timeout = 5.0
        start = time.time()
        while not future.done():
            time.sleep(0.05)
            if time.time() - start > timeout:
                self.get_logger().error('Timed out waiting for goal acceptance')
                return

        goal_handle = future.result()
        if not goal_handle.accepted:
            self.get_logger().warn('Action goal rejected')
            return

        result_future = goal_handle.get_result_async()
        start = time.time()
        while not result_future.done():
            time.sleep(0.05)
            if time.time() - start > 15.0:
                self.get_logger().error('Timed out waiting for action result')
                return

        result = result_future.result().result
        self.get_logger().info(f'Action result: {result.summary}')


def main(args=None):
    rclpy.init(args=args)
    node = SecurityResponseNode()
    # MultiThreadedExecutor is required — it lets the action server
    # execute_callback and the subscriber run in parallel
    executor = MultiThreadedExecutor()
    executor.add_node(node)
    try:
        executor.spin()
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
