require "test_helper"

class UpdatesControllerTest < ActionDispatch::IntegrationTest
  test "should get conversations" do
    get updates_conversations_url
    assert_response :success
  end

  test "should get messages" do
    get updates_messages_url
    assert_response :success
  end

  test "should get expert_queue" do
    get updates_expert_queue_url
    assert_response :success
  end
end
