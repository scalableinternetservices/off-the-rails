require "test_helper"

class ExpertControllerTest < ActionDispatch::IntegrationTest
  test "should get queue" do
    get expert_queue_url
    assert_response :success
  end

  test "should get claim" do
    get expert_claim_url
    assert_response :success
  end

  test "should get unclaim" do
    get expert_unclaim_url
    assert_response :success
  end

  test "should get profile" do
    get expert_profile_url
    assert_response :success
  end

  test "should get assignments_history" do
    get expert_assignments_history_url
    assert_response :success
  end
end
