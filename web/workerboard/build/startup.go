package main

import (
	"crypto/rand"
	"encoding/hex"
	"os"

	"workerboard/api"
)

func randomHexString(n int) string {
	r := make([]byte, n)
	rand.Read(r)
	return hex.EncodeToString(r)
}

func seedForum(forum *api.Server) error {

	user1, err := forum.AddUser("xXMeteorologyEnjoyerXx", randomHexString(32), false)
	if err != nil {
		return err
	}
	workerBody, _ := os.ReadFile("/app/default/weather.js")
	if _, err := forum.AddPost(user1, "whats your favorite kind of weather?!", string(workerBody), false); err != nil {
		return err
	}

	user2, err := forum.AddUser("literallyme124", randomHexString(32), false)
	if err != nil {
		return err
	}
	workerBody, _ = os.ReadFile("/app/default/likes.js")
	if _, err := forum.AddPost(user2, "like my post please please please", string(workerBody), false); err != nil {
		return err
	}

	user3, err := forum.AddUser("jamtothebeat", randomHexString(32), false)
	if err != nil {
		return err
	}
	workerBody, _ = os.ReadFile("/app/default/duck.js")
	if _, err := forum.AddPost(user3, "attempting to obtain a particular fruit", string(workerBody), false); err != nil {
		return err
	}

	adminAccount, err := forum.AddUser("admin", randomHexString(32), true)
	if err != nil {
		return err
	}
	workerBody, _ = os.ReadFile("/app/default/secret.js")
	if _, err := forum.AddPost(adminAccount, "secret!!!", string(workerBody), false); err != nil {
		return err
	}

	return nil
}
